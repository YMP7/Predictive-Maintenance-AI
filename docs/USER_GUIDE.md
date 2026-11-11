# ATLAS user guide

For operators and viewers: how to read the screens, handle alarms and act on a recommendation. Administrators also read [ADMIN_GUIDE.md](ADMIN_GUIDE.md).

## Signing in

Open the address your administrator gave you (for a local installation `http://localhost:8000`, or `http://localhost:3000` with the development server) and sign in. What you can do depends on your role:

| Role | Can |
|---|---|
| Viewer | Read every page outside administration |
| Operator | Everything a viewer can, plus acknowledge, shelve and clear alarms; create, approve, assign and close work orders; use agent chat |
| Admin | Everything, including administration and the Cognition dashboard |

Press **Ctrl K** anywhere to jump to a page by name. Times are shown in the zone in the header (Asia/Kolkata by default) with the zone written next to them; units are SI.

## Reading the screens

The screens follow ISA-101: grey when things are normal, colour only when something needs you.

- **Alarm colours** (ISA-18.2): critical, high, medium, low. Each comes with its own shape and a word, never colour alone.
- **Data-quality marks** beside a value:

| Mark | Meaning |
|---|---|
| SIMULATED | The value comes from a simulator, not a physical sensor |
| STALE | No update for more than three sampling intervals |
| RANGE | Outside the channel's valid range |
| FLATLINE | Unchanged for unusually long |
| MISSING | No value received |

- **Notices:**
  - A grey "Data is stale" bar means the page could not refresh; the values shown are the last ones received.
  - A red "Connection lost" bar means your browser is offline.
- **Machine status words:** C-MAPSS turbofans report Stable, Degrading or Critical; other machines report their adapter's status.
- **Health index:** 0% is a fresh machine, 100% is at its limit.
- **RUL (remaining useful life):** shown in the machine's own unit (cycles for the turbofan) with a ± band.

## Fleet overview (`/fleet`)

Start here. It shows:
- alarms that need acknowledging, highest priority first (with an "Alarm flood" mark when more than 10 arrive in 10 minutes);
- machines whose RUL is below 30% of their model's cap;
- every asset, worst first.

Select a tile to open the machine.

## A machine (`/assets/...`)

- **The 3D view:**
  - Drag to turn, scroll to zoom.
  - **Explode** pulls the parts apart; **Cutaway** opens the casing; **Isolate** shows one part.
  - Select a part, here or in the parts list, to see its sensors.
  - Part colours show load: orange is high, yellow elevated, grey normal. "Load" is a rule of thumb (how far the part's sensor is toward its limit), not a diagnosis.
- **Show why** (turbofans):
  - Lights the parts the RUL model leaned on; brighter means a larger share.
  - Other machines show the model's written justification instead.
- **Trends:** the RUL band and the selected part's sensors, since you opened the page.
- **Recommended action:**
  - **Get recommendation** runs the Decision Graph. It simulates each action 1,000 times and ranks them by expected cost.
  - If it suggests maintenance, **Create a work order for this action** opens a pre-filled order.

The Modbus pump shows RUL once it has sent 30 readings and its sensor profile matches the standard register map. Its model is trained on simulated run-to-failure data, so treat the value as a demonstration, not a measured forecast. **Show why** works for all five machine types.

## Alarms (`/alarms`)

The table is sorted by priority. Select a row for details; the address then points at that alarm, so you can share it.

- **Acknowledge:** you have seen it.
- **Shelve:** hide it for a set time (15 minutes to 24 hours) with a reason, for example during a planned sensor swap. When the time runs out it comes back unacknowledged.
- **Clear:** the condition is resolved. ATLAS does not yet detect this by itself, so give a reason.
- **Create a work order for this alarm:** opens a pre-filled order.

Every action is recorded with your name and reason.

## Work orders (`/work-orders`)

- **Lifecycle:**
  - Orders start as *Pending Approval*. **Approve** makes them *Open*; **Reject** (with a reason) closes them.
  - **Start** marks work *In Progress*; **Resolve** closes it.
  - Each step asks you to confirm.
- **Assigning:** in an order's detail panel, pick an operator or admin.
- **Agent orders:** orders the maintenance agent creates arrive *Pending Approval* like any other; nothing reaches the plant without a person approving it.

## Cross-domain view and Evidence

- **Cross-domain view** (`/cross-domain`): every machine on one normalised scale, to compare unlike machines.
- **Evidence** (`/about/evidence`): what each word of the title means here, where to see it and the number behind it.

## Agent chat (`/chat`, operators and admins)

Ask about a machine in plain language. With a machine selected, each answer shows the AMKB evidence for it: the similar past cases the explanation engine found.

## When something looks wrong

| You see | Do |
|---|---|
| "API unreachable" in the header | The server is down or restarting. Values stay on screen but stop updating; tell your administrator |
| "Data is stale" on a page | The page could not refresh for a while. Wait, or select Try again |
| A machine with "No data" | Its device has not sent anything yet. An administrator can check it on the Devices page |
| "Not available for your role" | The page needs another role. Ask an administrator |
