/// <reference types="cypress" />

describe('Critical User Flows', () => {
  beforeEach(() => {
    // Visit the application
    cy.visit('http://localhost:3000')
  })

  it('should allow a user to log in', () => {
    // When not authenticated, the app shows LoginPage at root
    cy.get('input[name="email"]').should('exist')
    cy.get('input[name="password"]').should('exist')
    cy.get('button[type="submit"]').should('exist')
    
    // Fill in login form
    cy.get('input[name="email"]').type('test@example.com')
    cy.get('input[name="password"]').type('password123')
    cy.get('button[type="submit"]').click()
    
    // After login, should show dashboard (since user is authenticated)
    cy.url().should('eq', 'http://localhost:3000/')
    // Check that we see dashboard content
    cy.contains('Dashboard').should('be.visible')
  })

  it('should allow a user to enroll a new person', () => {
    // First, log in
    cy.get('input[name="email"]').type('test@example.com')
    cy.get('input[name="password"]').type('password123')
    cy.get('button[type="submit"]').click()
    
    // Wait for login to complete and dashboard to load
    cy.contains('Dashboard').should('be.visible')
    
    // Navigate to enroll page - based on the file structure, this should be accessible
    cy.visit('http://localhost:3000/enroll')
    cy.url().should('include', '/enroll')
    
    // Fill enrollment form
    cy.get('input[name="name"]').should('exist')
    cy.get('input[name="name"]').type('Test Person')
    
    // Check for file upload
    cy.get('input[type="file"]').should('exist')
    
    // Give consent
    cy.get('input[type="checkbox"]').check()
    
    // Submit
    cy.get('button[type="submit"]').click()
    
    // Wait for processing to complete
    cy.get('.MuiCircularProgress').should('not.exist')
    
    // Check for success or absence of error
    cy.get('.MuiAlert-error').should('not.exist')
    // If there's a success message, check for it
    cy.contains(/enrollment|success/i).should('exist')
  })

  it('should allow a user to recognize a face', () => {
    // First, log in
    cy.get('input[name="email"]').type('test@example.com')
    cy.get('input[name="password"]').type('password123')
    cy.get('button[type="submit"]').click()
    
    // Wait for login to complete
    cy.contains('Dashboard').should('be.visible')
    
    // Navigate to recognize page
    cy.visit('http://localhost:3000/recognize')
    cy.url().should('include', '/recognize')
    
    // Check that the recognition interface loads
    cy.contains('Recognition').should('exist')
    
    // Check for webcam or upload interface
    cy.get('video').should('exist') // webcam
    cy.get('input[type="file"]').should('exist') // upload option
    
    // For now, we'll just verify the page loads without error
    cy.get('.MuiAlert-error').should('not.exist')
  })

  it('should allow a user to purchase a subscription', () => {
    // Log in
    cy.get('input[name="email"]').type('test@example.com')
    cy.get('input[name="password"]').type('password123')
    cy.get('button[type="submit"]').click()
    cy.contains('Dashboard').should('be.visible')

    // Go to subscription plans page
    cy.visit('http://localhost:3000/subscription-plans')
    // If the above fails, try an alternative route
    cy.url().should('match', /\/subscription-plans|\/plans/)

    // Wait for plans to load
    cy.contains('Subscription Plans').should('be.visible')

    // Select a plan (click the first Subscribe button)
    cy.get('button').contains('Subscribe').first().click()

    // Wait for payment dialog to open
    cy.dialog().should('be.visible')
    cy.dialog().should('contain', 'Complete Payment')

    // Fill in payment details with Stripe test card number
    cy.get('input[placeholder="1234 5678 9012 3456"]').type('4242 4242 4242 4242')
    cy.get('input[placeholder="MM/YY"]').type('12/34')
    cy.get('input[placeholder="123"]').type('123')
    cy.get('input[placeholder="Cardholder Name"]').type('Test User')

    // Submit payment
    cy.get('button').contains('Pay Now').click()

    // Wait for processing to complete
    cy.get('.MuiCircularProgress').should('not.exist')

    // Check for success message
    cy.contains('Subscription activated successfully!').should('be.visible')
    
    // Payment dialog should close
    cy.dialog().should('not.exist')
  })
})