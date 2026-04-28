# Frontend Component Documentation

## Overview

The AI-f frontend is built with React 18, Redux Toolkit, and TypeScript. The component architecture follows a modular approach with reusable components organized by feature.

## Component Structure

```
src/components/
├── Layout Components
│   ├── Sidebar.js
│   └── ...
├── Feature Components
│   ├── EnrichmentPortalPanel.js
│   ├── OrgSwitcher.js
│   ├── IncidentAlertDashboard.js
│   ├── AuditTimeline.js
│   ├── RBACGuard.js
│   ├── RecognitionErrorRecovery.js
│   ├── DashboardIntelligencePanel.js
│   ├── OperatorWorkflowPanel.js
│   ├── ExplainableAIPanel.js
│   ├── SetupWizard.js
│   ├── SystemStatus.js
│   ├── UploadBox.js
│   ├── WebcamCapture.js
│   └── ResultCard.js
└── Shared Components
    (if any)
```

## Component Descriptions

### Layout Components

#### Sidebar.js
Provides the main navigation sidebar for the application. Includes links to different sections based on user role and permissions.

### Feature Components

#### EnrichmentPortalPanel.js
Panel for public enrichment search functionality, allowing users to search for information about individuals using public data sources.

#### OrgSwitcher.js
Component that allows users to switch between different organizations they belong to, updating the current organization context.

#### IncidentAlertDashboard.js
Dashboard for displaying and managing security incidents, alerts, and responses.

#### AuditTimeline.js
Visual timeline component for displaying audit log entries in chronological order with filtering capabilities.

#### RBACGuard.js
Higher-order component that wraps routes or components to enforce role-based access control based on the user's permissions.

#### RecognitionErrorRecovery.js
Component that handles recovery from recognition errors, providing fallback options and user guidance when biometric recognition fails.

#### DashboardIntelligencePanel.js
Panel on the main dashboard that displays AI-driven insights, analytics, and recommendations based on recognition data.

#### OperatorWorkflowPanel.js
Panel designed for operators that provides quick access to common workflows like enrolling new individuals, starting recognition streams, etc.

#### ExplainableAIPanel.js
Component that displays explainable AI information for recognition decisions, showing why a particular match was made or not made.

#### SetupWizard.js
Multi-step wizard for initial setup of the system, including organization creation, admin user setup, and initial configuration.

#### SystemStatus.js
Component that displays the current status of various system components (database, Redis, ML models, etc.) with health indicators.

#### UploadBox.js
Reusable file upload component with drag-and-drop support, progress indicators, and validation for different file types (images, videos, audio).

#### WebcamCapture.js
Component for capturing video from webcam, including controls for starting/stopping capture, switching cameras, and taking snapshots.

#### ResultCard.js
Card component for displaying recognition results, including confidence scores, biometric modalities used, and action buttons.

## Styling

Components use a combination of CSS modules and styled-components for styling. Theme variables are defined in `src/styles/theme.js`.

## State Management

Components interact with the Redux store via hooks (`useAppDispatch`, `useAppSelector`) and RTK Query endpoints for data fetching.

## Testing

Unit tests for components are located in `__tests__` directories alongside the components or in `src/components/__tests__`.
