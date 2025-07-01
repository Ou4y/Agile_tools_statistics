# learn-curve-dashboard

A minimal Flask web app to upload Jira/Trello CSV logs, analyze user activity, collect survey answers, and visualize metrics with Plotly.

## Features
- Upload Jira/Trello CSV log (exported via REST API or web UI)
- Calculates per-task metrics:
  - `days_to_start`: Days from task creation to work start
  - `days_to_complete`: Days from task creation to completion
  - `active_duration`, `total_duration`, `total_changes`, and platform breakdowns
- Collects user survey answers (with admin management)
- Interactive dashboard with Plotly (histograms, boxplots, heatmaps, pie charts)
- Bootstrap 5 styling
- Admin session expires after 30 minutes of inactivity

## Quickstart

1. **Clone & Install**
   ```sh
   git clone <repo-url>
   cd learn-curve-dashboard
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Set Environment Variables**
   - Create a `.env` file in the project root:
     ```sh
     echo "ADMIN_PASSWORD=your_admin_password" > .env
     ```
   - Or set `ADMIN_PASSWORD` in your shell before running.

3. **Run Locally**
   ```sh
   python app.py
   ```
   The app runs on [http://127.0.0.1:5050](http://127.0.0.1:5050)

## CSV Export Instructions

### Jira
- Go to Issues > Search for Issues
- Use filters as needed
- Click "Export" > "Export Excel CSV (All fields)"

### Trello
- Use the [Trello API](https://developer.atlassian.com/cloud/trello/rest/api-group-actions/) to export actions as CSV
- Or use Power-Ups/third-party tools to export board activity as CSV

## Usage
- Upload a CSV file on the main page.
- View interactive charts and survey results on the dashboard.
- Add or manage survey answers (admin password required).
- To upload a new CSV, click "Upload Another CSV" (required headers are shown on the upload page).
- You can go to the dashboard at any time from the upload page.

## Deploy

### Docker
```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5050
CMD ["python", "app.py"]
```

### Heroku
```
web: python app.py
```

---
MIT License
