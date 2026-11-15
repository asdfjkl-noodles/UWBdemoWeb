Terminal 1 — Start PostgreSQL

Open PowerShell and run:

docker start uwb-postgres

You should see:

uwb-postgres

Check that it is running:

docker ps

You should see uwb-postgres in the list.

========================================================================================

🟢 Terminal 2 — Start your Backend

Open a new PowerShell window:


cd D:\Project\uwb_hyperrtls_demo\backend


Activate your Python environment:


.\.venv\Scripts\Activate.ps1


You should now see something like:

(.venv) PS D:\Project\uwb_hyperrtls_demo\backend>


Start FastAPI:

uvicorn main:app --reload --host 127.0.0.1 --port 8000

You should see something similar to:

INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.

Do not close this terminal.

Now test it by opening:

http://127.0.0.1:8000/docs

=============================================================================================

🟢 Terminal 3 — Start the UWB Simulator

Open another new PowerShell window:

cd D:\Project\uwb_hyperrtls_demo\simulator

Activate the backend environment:

..\backend\.venv\Scripts\Activate.ps1

Then:

python uwb_simulator.py

You should see the simulator sending positions.

Something like:

Sending TAG001: x=6.03, y=8.55
Sending TAG002: x=6.94, y=2.81
Sending TAG003: x=7.18, y=8.38
=========================================================================================
Don't close this terminal either.

after that open:
http://127.0.0.1:8000 
for app