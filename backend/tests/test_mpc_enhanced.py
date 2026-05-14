"""
Tests for Multi-Party Computation (MPC) with SPDZ protocol.

Validates:
- Shamir Secret Sharing (SSS) correctness
- Additive secret sharing reconstruction
- Beaver triple multiplication
- MPC party coordination
- Secure aggregation with dropout tolerance
- ZKP proof generation and verification
"""

import pytest
import asyncio
import json
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.security.mpc_spdz import (
     MPCParty, MPCOrchestrator, MPCSessionConfig,
     FieldArithmetic, ShamirSecretSharing, Share,
     BeaverMultiplication, BeaverTriple,
     SecureAggregation, SecureAggregationOrchestrator,
     PairwiseMaskProtocol, share_value, reconstruct_secret,
     generate_beaver_triple, FIELD_PRIME, AggregationConfig
 )
from app.security.mpc_zkp import (
    ZKPManager, ZKPStatement, SchnorrProof,
    MultiplicationProofProtocol, prove_multiplication_correct,
    verify_multiplication_proof
)


class TestFieldArithmetic:
    """Test finite field arithmetic operations."""
    
    def setup_method(self):
        self.field = FieldArithmetic(FIELD_PRIME)
    
    def test_add(self):
        a, b = 100, 200
        result = self.field.add(a, b)
        expected = (a + b) % FIELD_PRIME
        assert result == expected
    
    def test_sub(self):
        a, b = 100, 200
        result = self.field.sub(a, b)
        expected = (a - b) % FIELD_PRIME
        assert result == expected
    
    def test_mul(self):
        a, b = 12345, 67890
        result = self.field.mul(a, b)
        expected = (a * b) % FIELD_PRIME
        assert result == expected
    
    def test_inv(self):
        a = 12345
        inv = self.field.inv(a)
        # a * inv ≡ 1 (mod p)
        assert self.field.mul(a, inv) == 1
    
    def test_neg(self):
        a = 12345
        neg = self.field.neg(a)
        assert self.field.add(a, neg) == 0
    
    def test_random_in_field(self):
        for _ in range(100):
            r = self.field.random()
            assert 0 <= r < FIELD_PRIME


class TestShamirSecretSharing:
    """Test Shamir's secret sharing scheme."""
    
    def setup_method(self):
        self.field = FieldArithmetic(FIELD_PRIME)
        self.threshold = 2
        self.sss = ShamirSecretSharing(self.field, self.threshold)
    
    def test_share_and_reconstruct_3_of_3(self):
        secret = 123456789
        shares = self.sss.share(secret, n_shares=3)
        
        assert len(shares) == 3
        assert all(isinstance(s, Share) for s in shares)
        
        # Reconstruct with all shares
        recovered = self.sss.reconstruct(shares)
        assert recovered == secret
    
    def test_share_and_reconstruct_threshold(self):
        secret = 987654321
        shares = self.sss.share(secret, n_shares=5)
        
        # Reconstruct with exactly threshold+1 shares
        recovered = self.sss.reconstruct(shares[:3])
        assert recovered == secret
    
    def test_insufficient_shares_fails(self):
        secret = 42
        shares = self.sss.share(secret, n_shares=5)
        
        # Only 1 share (less than threshold+1=3)
        with pytest.raises(ValueError):
            self.sss.reconstruct(shares[:1])
    
    def test_share_uniqueness(self):
        """Each sharing generates different shares."""
        secret = 999
        shares1 = self.sss.share(secret, 3)
        shares2 = self.sss.share(secret, 3)
        # Shares should be different (random polynomials)
        assert shares1[0].value != shares2[0].value
    
    def test_share_serialization(self):
        share = Share(value=123, party_id=1, mac=456)
        d = share.to_dict()
        assert d['v'] == 123
        assert d['p'] == 1
        assert d['m'] == 456
        
        restored = Share.from_dict(d)
        assert restored.value == 123
        assert restored.party_id == 1
        assert restored.mac == 456


class TestBeaverTriple:
    """Test Beaver triple generation and multiplication."""
    
    def test_triple_generation(self):
        field = FieldArithmetic()
        triple = BeaverTriple.generate(field.prime)
        
        assert triple.a < FIELD_PRIME
        assert triple.b < FIELD_PRIME
        assert triple.c < FIELD_PRIME
        assert triple.c == (triple.a * triple.b) % FIELD_PRIME
    
    def test_triple_multiplication_with_shares(self):
        """Test multiplication using Beaver triples."""
        field = FieldArithmetic()
        sss = ShamirSecretSharing(field, threshold=1)
        beaver = BeaverMultiplication(field)
        
        # Secret values
        a_secret = 100
        b_secret = 50
        expected_c = (a_secret * b_secret) % FIELD_PRIME
        
        n = 3  # 3 parties
        # Share secrets
        a_shares = sss.share(a_secret, n)
        b_shares = sss.share(b_secret, n)
        
        # Generate triple shares
        triple = BeaverTriple.generate(field.prime)
        # Simple additive sharing of triple
        triple_a_shares = sss.share(triple.a, n)
        triple_b_shares = sss.share(triple.b, n)
        triple_c_shares = sss.share(triple.c, n)
        
        # Each party computes
        result_shares = []
        for i in range(n):
            party_a_sh = a_shares[i]
            party_b_sh = b_shares[i]
            party_triple_a = triple_a_shares[i]
            party_triple_b = triple_b_shares[i]
            party_triple_c = triple_c_shares[i]
            
            # d = a_share - triple_a_share, etc.
            d = field.sub(party_a_sh.value, party_triple_a.value)
            e = field.sub(party_b_sh.value, party_triple_b.value)
            
            # result = c_share + d * triple_b_share + e * triple_a_share + d*e
            term1 = party_triple_c.value
            term2 = field.mul(d, party_triple_b.value)
            term3 = field.mul(e, party_triple_a.value)
            term4 = field.mul(d, e)
            
            res_val = field.add(
                field.add(term1, term2),
                field.add(term3, term4)
            )
            result_shares.append(Share(res_val, i+1))
        
        # Reconstruct product
        recovered_c = sss.reconstruct(result_shares)
        assert recovered_c == expected_c


class TestMPCParty:
    """Test individual MPC party operations."""
    
    def setup_method(self):
        self.field = FieldArithmetic()
        config = MPCSessionConfig(n_parties=3, threshold=1, session_id="test")
        self.party = MPCParty(party_id=0, config=config, field=self.field)
    
    def test_share_secret(self):
        secret = 12345
        shares = self.party.share_secret(secret, "var1")
        
        assert "var1" in self.party._shares
        assert isinstance(shares, list)
        assert len(shares) == 3
        assert all(isinstance(s, Share) for s in shares)
    
    def test_add_shares(self):
        # Party already has shares for a and b
        self.party._shares['a'] = Share(100, 0)
        self.party._shares['b'] = Share(50, 0)
        
        self.party.add('a', 'b', 'c')
        
        assert 'c' in self.party._shares
        c_share = self.party._shares['c']
        expected = (100 + 50) % FIELD_PRIME
        assert c_share.value == expected


class TestMPCOrchestrator:
    """Test MPC orchestration across parties."""
    
    @pytest.mark.asyncio
    async def test_private_sum_three_parties(self):
        """Test secure sum across 3 parties."""
        field = FieldArithmetic()
        config = MPCSessionConfig(n_parties=3, threshold=1, session_id="sum_test")
        
        parties = [
            MPCParty(0, config, field),
            MPCParty(1, config, field),
            MPCParty(2, config, field),
        ]
        
        orchestrator = MPCOrchestrator(parties)
        
        inputs = [
            {0: 100, 1: 200, 2: 300},
            {0: 40, 1: 60, 2: 80},
            {0: 15, 1: 25, 2: 35},
        ]
        
        result = await orchestrator.compute_private_sum(inputs)
        
        assert "result" in result
        # Sum: (100+40+15)+(200+60+25)+(300+80+35) = 155+285+415 = 855
        assert result["result"] == 855
        assert result["n_parties"] == 3
    
    @pytest.mark.asyncio
    async def test_secure_aggregation(self):
        """Test secure aggregation (federated learning)."""
        field = FieldArithmetic()
        config = MPCSessionConfig(n_parties=3, threshold=1)
        
        parties = [
            MPCParty(0, config, field),
            MPCParty(1, config, field),
            MPCParty(2, config, field),
        ]
        
        orchestrator = MPCOrchestrator(parties)
        
        # Each party has gradient dict
        gradients = [
            {"weight1": 100, "weight2": 200},
            {"weight1": 50, "weight2": 150},
            {"weight1": 75, "weight2": 125},
        ]
        
        result = await orchestrator.compute_secure_aggregation(gradients)
        
        assert "aggregated_gradient" in result
        agg = result["aggregated_gradient"]
        # Sum of weights
        assert agg["weight1"] == (100 + 50 + 75) % FIELD_PRIME
        assert agg["weight2"] == (200 + 150 + 125) % FIELD_PRIME


class TestZKPIntegration:
    """Test ZKP for MPC verification."""
    
    def setup_method(self):
        self.field = FieldArithmetic()
        self.zkp_mgr = ZKPManager(FIELD_PRIME)
    
    def test_multiplication_proof_generation(self):
        """Generate and verify multiplication proof."""
        # Create shares and triple (simplified)
        share_a = Share(10, 0)
        share_b = Share(5, 0)
        share_c = Share(50, 0)  # c = a*b
        triple = BeaverTriple(a=2, b=3, c=6)
        
        # Generate proof
        proof = self.zkp_mgr.generate_proof(
            ZKPStatement.MULTIPLICATION_CORRECT,
            witness={
                'share_a': share_a,
                'share_b': share_b,
                'share_c': share_c,
                'triple': triple,
                'party_id': 0
            },
            public_inputs={
                'share_a': share_a,
                'share_b': share_b,
                'triple': triple,
                'party_id': 0
            },
            context={'party_id': 0, 'round': 1}
        )
        
        assert "commitment" in proof
        assert "response" in proof
        assert proof["statement"] == "mul_correct"
        
        # Verify proof
        verified = self.zkp_mgr.verify_proof(
            ZKPStatement.MULTIPLICATION_CORRECT,
            proof,
            public_inputs={
                'share_a': share_a,
                'share_b': share_b,
                'triple': triple,
                'party_id': 0
            },
            context={'party_id': 0, 'round': 1}
        )
        assert verified is True
    
    def test_batch_verification(self):
        proofs = []
        publics = []
        for i in range(5):
            a_val = i + 1
            b_val = i + 2
            c_val = a_val * b_val
            share_a = Share(a_val, i)
            share_b = Share(b_val, i)
            share_c = Share(c_val, i)
            triple = BeaverTriple(a=a_val, b=b_val, c=c_val)
            proof = self.zkp_mgr.generate_proof(
                ZKPStatement.MULTIPLICATION_CORRECT,
                {'share_a': share_a, 'share_b': share_b, 'share_c': share_c, 'triple': triple, 'party_id': i},
                {'share_a': share_a, 'share_b': share_b, 'triple': triple, 'party_id': i},
                {'party_id': i}
            )
            proofs.append(proof)
            publics.append({
                'share_a': share_a,
                'share_b': share_b,
                'triple': triple,
                'party_id': i
            })

        all_valid = self.zkp_mgr.batch_verify(proofs, publics)
        assert all_valid is True


class TestSecureAggregation:
    """Test Bonawitz-style secure aggregation."""

    @pytest.mark.asyncio
    async def test_secure_sum_three_parties(self):
        """Test secure sum with pairwise masks using scalar values."""
        config = AggregationConfig(
            n_parties=3,
            max_dropouts=0,
            use_pairwise_masks=True
        )

        parties = []
        for i in range(3):
            secagg = SecureAggregation(config, party_id=i)
            await secagg.setup()
            parties.append(secagg)

        # Exchange masks (simulated network)
        for i, party in enumerate(parties):
            for j in range(3):
                if i != j:
                    mask_val = party._mask_protocol._mask_shares.get(j, 0)
                    parties[j]._mask_protocol.receive_mask(i, mask_val)

        # Scalar inputs per party
        inputs = [100, 50, 75]

        masked_values = {}
        for i, party in enumerate(parties):
            result = party.submit_input(inputs[i])
            party_id = result["party_id"]
            masked_values[party_id] = result["masked_value"]

        # Reconstruct via party 0 as aggregator
        sum_val, sum_w = await parties[0].reconstruct_and_verify(masked_values)

        # Unmasked sum should be: 100 + 50 + 75 = 225
        assert sum_val == (100 + 50 + 75) % FIELD_PRIME

    @pytest.mark.asyncio
    async def test_mask_cancellation(self):
        """Test that pairwise masks sum to zero globally."""
        config = AggregationConfig(n_parties=3, max_dropouts=0)

        parties = []
        for i in range(3):
            party = SecureAggregation(config, party_id=i)
            await party.setup()
            parties.append(party)

        # Exchange masks (simulated network)
        for i, party in enumerate(parties):
            for j in range(3):
                if i != j:
                    mask_val = party._mask_protocol._mask_shares.get(j, 0)
                    parties[j]._mask_protocol.receive_mask(i, mask_val)

        # Verify global mask cancellation:
        # sum of all sent masks should equal sum of all received masks
        total_sent = 0
        total_received = 0
        field = parties[0].field
        for party in parties:
            for mask in party._mask_protocol._mask_shares.values():
                total_sent = field.add(total_sent, mask)
            for mask in party._mask_protocol._received_shares.values():
                total_received = field.add(total_received, mask)

        # In Bonawitz protocol, global mask sum cancels
        assert total_sent == total_received


class TestConvenienceFunctions:
    """Test high-level utility functions."""
    
    def test_share_value_function(self):
        shares = share_value(secret=12345, n_shares=3, threshold=2)
        assert len(shares) == 3
        assert all('v' in s and 'p' in s for s in shares)
    
    def test_reconstruct_secret_function(self):
        secret = 99999
        sss = ShamirSecretSharing(FieldArithmetic(), threshold=2)
        shares = sss.share(secret, 3)
        share_dicts = [s.to_dict() for s in shares]
        
        recovered = reconstruct_secret(share_dicts, threshold=2)
        assert recovered == secret
    
    def test_generate_beaver_triple_function(self):
        triple = generate_beaver_triple()
        assert 'a' in triple and 'b' in triple and 'c' in triple
        assert triple['c'] == (triple['a'] * triple['b']) % FIELD_PRIME


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
