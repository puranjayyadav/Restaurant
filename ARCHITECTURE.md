# Flutter Frontend Architecture

This document outlines the architecture of the Flutter frontend for the Food Explorer application.

## 1. Project Structure

The project follows a feature-based organization, with code separated into the following main directories under `lib/`:

-   **`screens`**: Contains the main pages or screens of the application. Each screen is a separate widget.
-   **`widgets`**: Contains reusable UI components that are used across multiple screens. This promotes code reuse and a consistent UI.
-   **`services`**: Contains business logic and services that interact with external systems like Firebase and other APIs. This separates the data layer from the UI layer.
-   **`theme`**: Contains the design system, including colors, typography, and other styling information.
-   **`api_service.dart`**: A dedicated service for making API calls to the backend.
-   **`main.dart`**: The entry point of the application. It initializes the app and sets up the initial routing.

## 2. Application Flow & Navigation

The application's navigation is centered around a main `BottomNavigationBar`. The flow is as follows:

1.  **Entry Point (`main.dart`)**:
    *   The `main()` function initializes Firebase.
    *   It checks if a user is authenticated with Firebase Auth.
    *   **If not authenticated**: It displays the `GoogleSignInScreen` (`google_signin_screen.dart`).
    *   **If authenticated**:
        *   It checks if the user has set their preferences by looking for a document in the `user_preferences` collection in Firestore.
        *   **If preferences are set**: It navigates to the `PlanditExploreScreen`.
        *   **If preferences are not set**: It navigates to the `PreferenceSelectionScreen`.

2.  **Preference Selection (`lib/screens/preference_selection_screen.dart`)**:
    *   This screen is shown to new users after they sign in for the first time.
    *   It fetches a list of places the user has previously visited from the `establishments` collection in Firestore.
    *   The user can select their favorite places from this list.
    *   Upon completion, the selected preferences are saved to the `user_preferences` collection in Firestore, and the user is navigated to the main application screen (`MainScreen`).

3.  **Main Screen (`lib/main.dart`)**:
    *   The `MainScreen` is a `StatefulWidget` that holds a `BottomNavigationBar`.
    *   The `BottomNavigationBar` allows the user to switch between the four main sections of the app:
        *   **Discover**: `PlanditExploreScreen` (`lib/screens/plandit_explore_screen.dart`) - This is the main dashboard of the app.
        *   **My Plans**: `SavedItinerariesScreen` (`lib/screens/saved_itineraries_screen.dart`) - Shows itineraries saved by the user.
        *   **Saved**: `PublicItinerariesScreen` (`lib/screens/public_itineraries_screen.dart`) - A feed of public itineraries from other users.
        *   **Profile**: `SettingsScreen` (`lib/screens/settings_screen.dart`) - User profile and settings.

## 3. Screen Breakdown

### 3.1. `PlanditExploreScreen` (`lib/screens/plandit_explore_screen.dart`)

*   **Purpose**: This is the main dashboard or "home" screen of the application. It appears to be part of a larger feature called "Plandit".
*   **Structure**: This screen has its own nested bottom navigation, which suggests it's a self-contained hub.
*   **Components**:
    *   `PlanditDashboardHeader`: The header for the dashboard.
    *   `PlanditAskAISection`: A section for interacting with an AI.
    *   `PlanditNeighborhoodSpotlight`: Highlights a specific neighborhood.
    *   `PlanditWeekendEdit`: Suggestions for the weekend.
    *   `PlanditUpcomingTrip`: Shows an upcoming trip.
    *   `PlanditCuratedCategories`: A list of curated categories.
*   **Navigation**: The nested bottom navigation switches between the dashboard, a search/explore screen (`PlanditIndexScreen`), a placeholder for a "Create" feature, the `SavedItinerariesScreen`, and the `SettingsScreen`.

### 3.2. `SavedItinerariesScreen` (`lib/screens/saved_itineraries_screen.dart`)

*   **Purpose**: Displays itineraries that the user has saved.
*   **Data Source**: Fetches data from the `saved_itineraries` collection in Firestore.
*   **Features**:
    *   A `TabBar` to switch between "DAY PLANS" and "LOVED SPOTS" (`LovedPlacesScreen`).
    *   Itineraries are displayed in expandable cards (`_ExpandableItineraryCard`).
    *   **Actions**:
        *   Navigate, Edit, Duplicate, Share, Submit to Public, Export to Calendar, and Delete itineraries.
        *   Navigation and editing are handled by the `ScoutModeScreen`.
        *   Submitting to public is handled by `SubmitItineraryScreen`.

### 3.3. `PublicItinerariesScreen` (`lib/screens/public_itineraries_screen.dart`)

*   **Purpose**: A social feed of public itineraries created by other users.
*   **Data Source**: Fetches data from a backend API via the `ApiService`.
*   **Features**:
    *   Infinite scrolling list of public itineraries.
    *   Search by location.
    *   Sort by "Most Recent" or "Most Liked".
    *   Filter by categories.
    *   Users can "like" and "share" public itineraries.
    *   Tapping an itinerary opens the `PublicItineraryDetailScreen`.

### 3.4. `SettingsScreen` (`lib/screens/settings_screen.dart`)

*   **Purpose**: Displays user information and provides a way to sign out.
*   **Features**:
    *   Displays the user's profile picture, name, and email.
    *   A "Sign Out" button that logs the user out and returns them to the `GoogleSignInScreen`.
    *   Displays app information like version number.

## 4. Services

### 4.1. `firebase_service.dart`

*   This file was not reviewed but is presumed to handle interactions with Firebase services like Authentication and Firestore.

### 4.2. `api_service.dart`

*   This service is responsible for all communication with the backend API.
*   It is used by `PublicItinerariesScreen` to fetch, share, and interact with public itineraries.

### 4.3. `location_service.dart`

*   This file was not reviewed but is likely responsible for handling device location services, such as getting the user's current location.

### 4.4. `user_preferences_service.dart`

*   This service, used by `PreferenceSelectionScreen`, is responsible for saving and retrieving user preferences from Firestore.

## 5. Key Widgets

*   **`Plandit*` widgets (`lib/widgets/plandit/`)**: A collection of widgets that make up the "Plandit" feature, indicating a modular and reusable design.
*   **`_ExpandableItineraryCard` (`lib/screens/saved_itineraries_screen.dart`)**: A complex widget that displays a saved itinerary and provides numerous actions.
*   **`LikeButton` (`lib/widgets/like_button.dart`)**: A reusable widget for liking public itineraries.
*   **`UserProfileCard` (`lib/widgets/user_profile_card.dart`)**: A reusable widget to display user profile information.

## 6. Data Models

While not explicitly defined in separate files, the data structures are implied by their usage:

*   **User**: Managed by Firebase Authentication.
*   **User Preferences**: A document in the `user_preferences` collection in Firestore, containing a list of favorite place IDs.
*   **Saved Itinerary**: A document in the `saved_itineraries` collection in Firestore. It contains a user ID, creation date, location, and a list of items (places) in the itinerary.
*   **Public Itinerary**: Fetched from the API. It includes a title, description, location, categories, user information, likes count, and a list of items.

This architecture promotes a clean separation of concerns, making the application scalable and maintainable.
