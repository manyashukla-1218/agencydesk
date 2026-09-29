from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, projects, tasks, files, time_entries, invites, dashboard, clients, members

app = FastAPI(title="AgencyDesk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(files.router)
app.include_router(time_entries.router)
app.include_router(invites.router)
app.include_router(dashboard.router)
app.include_router(members.router)


@app.get("/health")
def health():
    return {"status": "ok"}
