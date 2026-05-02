{
  "e2e": {
    "baseUrl": "http://localhost:3000",
    "specPattern": "cypress/e2e/**/*.cy.{js,jsx,ts,tsx}",
    "supportFile": "cypress/support/e2e.js",
    "video": false,
    "screenshotOnRunFailure": true,
    "env": {
      "apiUrl": "http://localhost:8000"
    }
  }
}