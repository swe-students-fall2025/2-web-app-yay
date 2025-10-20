# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Product vision statement

Our vision is to create a simple, user-friendly to-do list web application that helps students and professionals stay organized, productive, and focused by allowing them to easily create, categorize, and track their tasks.

## User stories
### 🏠 landing page
- As a visitor to the Todo App website, I can understand what the app does in the landing page and how to get started, so that I can decide if it's worth signing up for.

### 📝 signup page
- As a non-registered user, I can register a new account with the site, so that I can start organizing and tracking my tasks.

### 🔐 login page
- As a user, I can log in to the site, so that I can access my personalized dashboard and manage my tasks.

### 📋 dashboard page
- As a user, I can access my personalized dashboard and manage my tasks with the to-do lists summary and reminders, so that I stay informed about upcoming deadlines and pending tasks.
- As a user, I can create categories for school, work, projects, etc., so that I can organize my tasks by context.
- As a user, I want to filter the tasks based on priority, so that I can view high-priority tasks at the top and low-priority tasks at the bottom.
- As a user, I can read reminders in the dashboard page that tell me which due dates are approaching, so I don't miss my deadlines.
- As a user, I can use the search bar in the dashboard screen, so that I can search for a certain task and see the progress.
- As a user, I can use the sort button to see the priority from high to low, so I know which tasks I should prioritize.
- As a user, I can mark tasks as completed, so that I know which tasks are finished and can focus on the remaining ones.

### ➕ add task page
- As a user, I can create tasks within a category with details like title, priority, and due dates, so that I can keep track of what needs to be done and by when.

### ✏️ edit_task page
- As a user, I can edit a task’s due date and description, so that I can update my schedule when deadlines or task details change.

### 📊 todo_history page
- As a user, I can see statistics about my completed tasks in the history page, so that I can track my productivity.

## Steps necessary to run the software

### Prerequisites
- Python 3.9 or higher
- pip (Python package installer)

### Installation and Setup

1. **Install pipenv** (if not already installed)
   ```bash
   pip install pipenv
   ```
   Or on macOS with Homebrew:
   ```bash
   brew install pipenv
   ```

2. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd 2-web-app-yay
   ```

3. **Install dependencies**
   ```bash
   pipenv install
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root with the following variables:
   ```
   PORT=3000
   SECRET_KEY=your-secret-key-here
   MONGO_URI=your-mongodb-connection-string
   MONGO_DB=todoapp
   ```

5. **Run the application**
   ```bash
   pipenv run python app.py
   ```

6. **Access the application**
   
   Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

## Task boards

[Sprint 1](https://github.com/orgs/swe-students-fall2025/projects/13)
[Sprint 2](https://github.com/orgs/swe-students-fall2025/projects/50)

### Sprint Planning Notes

All user stories were planned and created during Sprint 1. At the end of Sprint 1, we moved any incomplete tickets (those in "To Do" or "In Progress" columns) to the Sprint 2 board to continue working on them. This ensures proper sprint management and allows us to track our progress across both sprints while maintaining visibility of all work items.
