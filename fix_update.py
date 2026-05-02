f = open("backend/enclave_mock.py", "r")
c = f.read()
f.close()
old = """                else:
                    response = {
                        'id': request_id,
                        'error': 'Unknown operation',
                        'status': 'error'
                    }"""
print("found:", old in c)
parts = c.split(old)
print("parts:", len(parts))
n = '''                elif operation == "add_known_voice_embedding":
                    if "embedding" not in request or "label" not in request:
                        self._send_error(conn,"Missing")
                        continue
                    ne=np.array(request["embedding"],dtype=np.float32)
                    lb=request["label"]
                    p="known_voice_embeddings.npy"
                    if os.path.exists(p): ve=np.load(p)
                    else: ve=np.array([]).reshape(0,192)
                    if ve.size==0: ve=ne.reshape(1,-1)
                    else: ve=np.vstack([ve,ne])
                    np.save(p,ve)
                    response={"id":request_id,"result":{"message":"Voice "+lb,"total":ve.shape[0]},"status":"success"}
                elif operation == "add_known_gait_embedding":
                    if "embedding" not in request or "label" not in request:
                        self._send_error(conn,"Missing")
                        continue
                    ne=np.array(request["embedding"],dtype=np.float32)
                    lb=request["label"]
                    p="known_gait_embeddings.npy"
                    if os.path.exists(p): ge=np.load(p)
                    else: ge=np.array([]).reshape(0,7)
                    if ge.size==0: ge=ne.reshape(1,-1)
                    else: ge=np.vstack([ge,ne])
                    np.save(p,ge)
                    response={"id":request_id,"result":{"message":"Gait "+lb,"total":ge.shape[0]},"status":"success"}
                elif operation == "voice_match":
                    if "embedding" not in request:
                        self._send_error(conn,"Missing")
                        continue
                    ie=np.array(request["embedding"],dtype=np.float32)
                    p="known_voice_embeddings.npy"
                    if os.path.exists(p): k=np.load(p)
                    else: k=np.array([]).reshape(0,192)
                    if k.size==0: response={"id":request_id,"result":{"matched":False,"similarity":0.0},"status":"success"}
                    else:
                        sims=np.dot(k,ie)/(np.linalg.norm(k,axis=1)*np.linalg.norm(ie)+1e-10)
                        bi=int(np.argmax(sims))
                        bs=float(sims[bi])
                        response={"id":request_id,"result":{"matched":bool(bs>=0.65),"index":bi,"similarity":bs},"status":"success"}
                elif operation == "gait_match":
                    if "embedding" not in request:
                        self._send_error(conn,"Missing")
                        continue
                    ie=np.array(request["embedding"],dtype=np.float32)
                    p="known_gait_embeddings.npy"
                    if os.path.exists(p): k=np.load(p)
                    else: k=np.array([]).reshape(0,7)
                    if k.size==0: response={"id":request_id,"result":{"matched":False,"similarity":0.0},"status":"success"}
                    else:
                        sims=np.dot(k,ie)/(np.linalg.norm(k,axis=1)*np.linalg.norm(ie)+1e-10)
                        bi=int(np.argmax(sims))
                        bs=float(sims[bi])
                        response={"id":request_id,"result":{"matched":bool(bs>=0.65),"index":bi,"similarity":bs},"status":"success"}
                elif operation == "get_enclave_info":
                    response={"id":request_id,"result":{"enclave_type":"mock_tee","attestation":{"type":"mock_sgx","mr_enclave":"abc123","mr_signer":"def456"}},"status":"success"}
                else:'''
result = n.join(parts)
with open("backend/enclave_mock.py", "w") as f:
    f.write(result)
print("Updated")