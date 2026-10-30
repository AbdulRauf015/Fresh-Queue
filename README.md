# FreshQueue - Grocery Stock Manager (Queue / FIFO)

DSA Open Ended Lab (SW-212) - **Group C: Queue**.
**Backend: Java** (queue + all logic) - **Frontend: Python (Tkinter)** - made for shopkeepers.

## The problem
A grocery shop receives perishable goods (milk, bread, yogurt) in **batches**. If a newer batch is sold before
an older one, the older stock expires on the shelf. The rule is **First In, First Out**, exactly how a Queue works.

## How the Queue is used (Java backend)
| Shop action | Queue operation |
|---|---|
| Add new stock (Create) | `enqueue()` at the rear |
| See what to sell next (Read) | `peek()` at the front |
| Oldest stock finished (Delete) | `dequeue()` from the front |
| Show all / Search / Edit / Remove a chosen item | rotate the queue: dequeue every item once and enqueue it back |
| Record a sale (FIFO) | rotate once to check stock, rotate again taking pieces from the oldest batch first; an empty batch is not enqueued back |
| Remove expired stock | one rotation, expired batches are not enqueued back |
| Customer line at the counter | a second queue: customer joins = enqueue, "call next" = dequeue |
| Sales history | a third queue, bounded to 50: when full, dequeue the oldest, then enqueue the new sale |

The queue is written from scratch with linked nodes (generic `LinkedQueue<T>` and `Node<T>`); `java.util.Queue` is not used.
The same class is used for the stock, the customer line and the sales history.
A queue has no random access, so Search/Edit/Remove-by-choice are O(n); enqueue, dequeue and peek are O(1).
The screen's **"How the Queue works"** button shows the queue as boxes and the real number of
enqueue/dequeue calls used by every action, and adds a **Speed Test** tab that measures every operation on queues of
100 to 20,000 items (O(1) vs O(n)) with charts and CSV export - material for the report's "Analysis & Results".

See **USER_GUIDE.md** for a full step-by-step example of a shop day.

## Architecture
```
Python screen (frontend/)  <--- local HTTP on 127.0.0.1 --->  Java backend (backend/)
  app.py   screens, buttons                                      Server.java            HTTP API
  api.py   sends requests                                        InventoryManager.java  CRUD using queue only
  texts.py English + Roman Urdu words                            LinkedQueue.java / Node.java  the Queue
                                                                 CustomerLine.java, SalesHistory.java (more queues)
                                                                 Benchmark.java, Product.java, Storage.java, Json.java
```
The Python program starts the Java backend by itself - the user just opens one program.
Stock and sales are saved in the `data` folder, so they are still there after restart (the customer line is not saved).

| Request | Meaning |
|---|---|
| `GET /items` | whole queue, front to rear, with summary numbers |
| `GET /search?q=milk` | items whose name/type contains the text |
| `POST /items` | Create (enqueue) |
| `PUT /items/{id}` | Update |
| `DELETE /items/{id}` | Delete a chosen item |
| `POST /sell-first` | Delete the oldest item (dequeue) |
| `POST /sale` | Record a sale, FIFO across batches |
| `POST /remove-expired` | Remove every expired batch |
| `GET /history` | Last 50 sales + today's totals |
| `GET /line`, `POST /line`, `POST /line/next` | Customer line: list, join, call next |
| `GET /benchmark` | Speed test on a temporary queue |

## Run
Extract the zip into a **new empty folder** (never over an older version).
Needs **JDK 11+** and **Python 3.8+** (Tkinter comes with the normal Python installer; no pip packages).
- Windows: double-click `run.bat`
- Linux/Mac: `sh run.sh`

The first start compiles the Java files automatically (a few seconds).

## v3 additions
Six colour themes (2 dark), one-click night mode, languages English / Roman Urdu / Urdu / Sindhi / Arabic (RTL layout), settings saved in `data/settings.json`, scrollable Speed Test page.
