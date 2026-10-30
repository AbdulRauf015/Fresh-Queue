import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;

/**
 * Backend of FreshQueue. All business logic (queue, CRUD, validation, expiry rules)
 * lives here in Java. The Python screen talks to it over a local HTTP connection
 * (127.0.0.1 only, never the internet).
 *
 *  GET    /health          is the backend alive?
 *  GET    /items           whole queue (front -> rear) + summary numbers
 *  GET    /search?q=text   items whose name/category contains text
 *  POST   /items           Create  -> enqueue at rear
 *  PUT    /items/{id}      Update
 *  DELETE /items/{id}      Delete a chosen item
 *  POST   /sell-first      Delete the oldest item -> dequeue from front
 *  POST   /sample          Load practice items
 *  POST   /sale            Record a sale: pieces are taken from the OLDEST batches first (FIFO)
 *  GET    /stock-names     items that can be sold now, with pieces available
 *  POST   /remove-expired  remove every expired batch
 *  GET    /history         last 50 sales (bounded queue) + today's totals
 *  GET    /line            customers waiting at the counter (queue)
 *  POST   /line            a customer joins the line (enqueue)
 *  POST   /line/next       call the next customer (dequeue)
 *  GET    /benchmark       speed test of queue operations on a temporary queue
 */
public class Server {
    private static final InventoryManager inv = new InventoryManager();
    private static final SalesHistory history = new SalesHistory();
    private static final CustomerLine line = new CustomerLine();

    public static void main(String[] args) throws IOException {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 8765;
        inv.bulkLoad(Storage.load());
        for (SaleRecord r : Storage.loadSales()) history.record(r);

        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/", Server::handle);
        // single thread on purpose: the queue is not thread-safe, requests are handled one by one
        server.setExecutor(Executors.newSingleThreadExecutor());
        server.start();
        System.out.println("FreshQueue backend running on port " + port);
    }

    // ------------------------------------------------------------ routing
    private static void handle(HttpExchange ex) throws IOException {
        try {
            String method = ex.getRequestMethod();
            String path = ex.getRequestURI().getPath();
            String query = ex.getRequestURI().getQuery();

            if (method.equals("GET") && path.equals("/health")) {
                send(ex, 200, "{\"ok\":true}");
            } else if (method.equals("GET") && path.equals("/items")) {
                send(ex, 200, listJson(inv.snapshot()));
            } else if (method.equals("GET") && path.equals("/search")) {
                String q = "";
                if (query != null && query.startsWith("q=")) {
                    q = java.net.URLDecoder.decode(query.substring(2), StandardCharsets.UTF_8);
                }
                send(ex, 200, q.isBlank() ? listJson(inv.snapshot()) : listJson(inv.search(q)));
            } else if (method.equals("POST") && path.equals("/items")) {
                create(ex);
            } else if (method.equals("PUT") && path.startsWith("/items/")) {
                update(ex, idFrom(path));
            } else if (method.equals("DELETE") && path.startsWith("/items/")) {
                delete(ex, idFrom(path));
            } else if (method.equals("POST") && path.equals("/sell-first")) {
                sellFirst(ex);
            } else if (method.equals("POST") && path.equals("/sample")) {
                loadSample(ex);
            } else if (method.equals("POST") && path.equals("/sale")) {
                sale(ex);
            } else if (method.equals("GET") && path.equals("/stock-names")) {
                send(ex, 200, stockNamesJson());
            } else if (method.equals("POST") && path.equals("/remove-expired")) {
                removeExpired(ex);
            } else if (method.equals("GET") && path.equals("/history")) {
                send(ex, 200, historyJson());
            } else if (method.equals("GET") && path.equals("/line")) {
                send(ex, 200, lineJson());
            } else if (method.equals("POST") && path.equals("/line")) {
                joinLine(ex);
            } else if (method.equals("POST") && path.equals("/line/next")) {
                callNext(ex);
            } else if (method.equals("GET") && path.equals("/benchmark")) {
                send(ex, 200, Benchmark.run(new int[]{100, 500, 1000, 5000, 10000, 20000}));
            } else {
                error(ex, 404, "Unknown request.");
            }
        } catch (IllegalArgumentException e) {
            error(ex, 400, e.getMessage());
        } catch (Exception e) {
            error(ex, 500, "Something went wrong inside the backend.");
        }
    }

    // ------------------------------------------------------------ actions
    private static void create(HttpExchange ex) throws IOException {
        Product p = parse(body(ex), inv.nextId());
        inv.create(p);
        save();
        mutation(ex, "CREATE", "enqueued '" + p.getName() + "' (#" + p.getId() + ") at the rear", "Saved.");
    }

    private static void update(HttpExchange ex, int id) throws IOException {
        Product p = parse(body(ex), id);
        if (!inv.update(id, p.getName(), p.getCategory(), p.getQuantity(), p.getPrice(), p.getExpiryDate())) {
            throw new IllegalArgumentException("This item was not found.");
        }
        save();
        mutation(ex, "UPDATE", "updated #" + id + " (queue rotated once, order unchanged)", "Saved.");
    }

    private static void delete(HttpExchange ex, int id) throws IOException {
        Product p = inv.deleteById(id);
        if (p == null) throw new IllegalArgumentException("This item was not found.");
        save();
        mutation(ex, "DELETE (by ID)", "removed '" + p.getName() + "' (#" + id + "), others re-enqueued in order",
                "Removed.");
    }

    private static void sellFirst(HttpExchange ex) throws IOException {
        Product p = inv.dequeueFront();
        if (p == null) throw new IllegalArgumentException("There is no stock to remove.");
        save();
        mutation(ex, "DELETE (FIFO)", "dequeued oldest batch '" + p.getName() + "' (#" + p.getId() + ")", "Done.");
    }

    private static void loadSample(HttpExchange ex) throws IOException {
        int added = 0;
        for (Product p : Storage.sample(inv.nextId())) {
            inv.create(p);
            added++;
        }
        save();
        mutation(ex, "CREATE", "enqueued " + added + " sample batches", "Practice items added.");
    }

    private static void sale(HttpExchange ex) throws IOException {
        Map<String, String> m = Json.parseObject(body(ex));
        String name = m.getOrDefault("name", "").trim();
        if (name.isEmpty()) throw new IllegalArgumentException("Please choose the item that was sold.");
        int qty;
        try {
            qty = Integer.parseInt(m.getOrDefault("quantity", "").trim());
            if (qty <= 0) throw new NumberFormatException();
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("'How many pieces' must be a whole number like 5.");
        }
        InventoryManager.SaleResult r = inv.sell(name, qty);
        if (r.error != null) throw new IllegalArgumentException(r.error);

        String when = java.time.LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
        history.record(new SaleRecord(when, r.itemName, qty, r.amount));
        Storage.saveSales(history.snapshot());
        save();

        StringBuilder parts = new StringBuilder("[");
        StringBuilder detail = new StringBuilder("sold " + qty + " x '" + r.itemName + "' taking from the oldest batches first:");
        for (int i = 0; i < r.parts.size(); i++) {
            InventoryManager.SalePart p = r.parts.get(i);
            if (i > 0) parts.append(',');
            parts.append("{\"id\":").append(p.id).append(",\"took\":").append(p.took)
                 .append(",\"finished\":").append(p.finished).append('}');
            detail.append(" batch #").append(p.id).append(" -").append(p.took).append(p.finished ? " (finished, left the queue)" : "").append(';');
        }
        parts.append(']');
        send(ex, 200, "{\"ok\":true,\"message\":" + Json.quote("Sale recorded.")
                + ",\"op\":\"SALE (FIFO)\",\"detail\":" + Json.quote(detail.toString())
                + ",\"enq\":" + inv.getEnqCount() + ",\"deq\":" + inv.getDeqCount()
                + ",\"itemName\":" + Json.quote(r.itemName) + ",\"quantity\":" + qty
                + ",\"amount\":" + r.amount + ",\"parts\":" + parts + "}");
    }

    private static void removeExpired(HttpExchange ex) throws IOException {
        List<Product> gone = inv.removeExpired();
        if (gone.isEmpty()) throw new IllegalArgumentException("Nothing has expired.");
        save();
        mutation(ex, "DELETE (expired)", "removed " + gone.size() + " expired batch(es) in one queue rotation",
                gone.size() + " expired item(s) removed.");
    }

    private static void joinLine(HttpExchange ex) throws IOException {
        Map<String, String> m = Json.parseObject(body(ex));
        String name = m.getOrDefault("name", "");
        if (name.length() > 40) throw new IllegalArgumentException("The name is too long.");
        Customer c = line.join(name);
        send(ex, 200, "{\"ok\":true,\"message\":" + Json.quote("Customer added to the line.")
                + ",\"op\":\"LINE JOIN\",\"detail\":" + Json.quote("enqueued " + c.name + " (token " + c.token + ") at the rear of the line")
                + ",\"enq\":1,\"deq\":0}");
    }

    private static void callNext(HttpExchange ex) throws IOException {
        Customer c = line.serveNext();
        if (c == null) throw new IllegalArgumentException("Nobody is waiting in the line.");
        send(ex, 200, "{\"ok\":true,\"message\":" + Json.quote("Now serving " + c.name + ".")
                + ",\"op\":\"LINE NEXT\",\"detail\":" + Json.quote("dequeued " + c.name + " (token " + c.token + ") from the front of the line")
                + ",\"enq\":0,\"deq\":1}");
    }

    // ------------------------------------------------------------ validation
    private static Product parse(String json, int id) {
        Map<String, String> m = Json.parseObject(json);
        String name = m.getOrDefault("name", "").trim();
        if (name.isEmpty()) throw new IllegalArgumentException("Please type the item name.");
        if (name.length() > 60) throw new IllegalArgumentException("The item name is too long.");
        String category = m.getOrDefault("category", "").trim();
        if (category.isEmpty()) category = "Other";
        int qty;
        try {
            qty = Integer.parseInt(m.getOrDefault("quantity", "").trim());
            if (qty < 0) throw new NumberFormatException();
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("'How many' must be a whole number like 10.");
        }
        double price;
        try {
            price = Double.parseDouble(m.getOrDefault("price", "").trim());
            if (price <= 0) throw new NumberFormatException();
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Price must be a number like 150.");
        }
        String expiry = m.getOrDefault("expiry", "").trim();
        try {
            LocalDate.parse(expiry);
        } catch (Exception e) {
            throw new IllegalArgumentException("Please choose a real expiry date.");
        }
        return new Product(id, name, category, qty, price, expiry);
    }

    // ------------------------------------------------------------ JSON output
    private static String productJson(Product p) {
        return "{\"id\":" + p.getId()
                + ",\"name\":" + Json.quote(p.getName())
                + ",\"category\":" + Json.quote(p.getCategory())
                + ",\"quantity\":" + p.getQuantity()
                + ",\"price\":" + p.getPrice()
                + ",\"expiry\":" + Json.quote(p.getExpiryDate())
                + ",\"daysLeft\":" + (p.daysLeft() == Long.MAX_VALUE ? 99999 : p.daysLeft())
                + ",\"low\":" + p.isLow() + "}";
    }

    private static String listJson(List<Product> items) {
        StringBuilder sb = new StringBuilder("{\"items\":[");
        int units = 0, soon = 0, low = 0, expired = 0;
        for (int i = 0; i < items.size(); i++) {
            Product p = items.get(i);
            if (i > 0) sb.append(',');
            sb.append(productJson(p));
        }
        sb.append("],\"stats\":");
        // statistics always describe the WHOLE stock, not just a search result
        List<Product> all = inv.snapshot();
        for (Product p : all) {
            units += p.getQuantity();
            if (p.daysLeft() >= 0 && p.daysLeft() <= 7) soon++;
            if (p.daysLeft() < 0) expired++;
            if (p.isLow()) low++;
        }
        Product next = inv.peekNext();
        sb.append("{\"batches\":").append(all.size())
          .append(",\"units\":").append(units)
          .append(",\"expiringSoon\":").append(soon)
          .append(",\"expired\":").append(expired)
          .append(",\"lowStock\":").append(low)
          .append(",\"next\":").append(next == null ? "null" : Json.quote(next.getName()))
          .append("},\"queue\":[");
        for (int i = 0; i < all.size(); i++) {
            Product p = all.get(i);
            if (i > 0) sb.append(',');
            sb.append("{\"id\":").append(p.getId()).append(",\"name\":").append(Json.quote(p.getName()))
              .append(",\"quantity\":").append(p.getQuantity()).append(",\"expiry\":")
              .append(Json.quote(p.getExpiryDate())).append('}');
        }
        return sb.append("]}").toString();
    }

    private static String stockNamesJson() {
        StringBuilder sb = new StringBuilder("{\"names\":[");
        boolean first = true;
        for (Map.Entry<String, Integer> e : inv.availableByName().entrySet()) {
            if (!first) sb.append(',');
            first = false;
            sb.append("{\"name\":").append(Json.quote(e.getKey())).append(",\"available\":").append(e.getValue()).append('}');
        }
        return sb.append("]}").toString();
    }

    private static String historyJson() {
        List<SaleRecord> all = history.snapshot();
        StringBuilder sb = new StringBuilder("{\"sales\":[");
        for (int i = 0; i < all.size(); i++) {
            SaleRecord r = all.get(i);
            if (i > 0) sb.append(',');
            sb.append("{\"time\":").append(Json.quote(r.time)).append(",\"item\":").append(Json.quote(r.itemName))
              .append(",\"quantity\":").append(r.quantity).append(",\"amount\":").append(r.amount).append('}');
        }
        return sb.append("],\"todayAmount\":").append(history.todayAmount())
                 .append(",\"todayPieces\":").append(history.todayPieces())
                 .append(",\"kept\":").append(all.size())
                 .append(",\"capacity\":").append(SalesHistory.CAPACITY).append('}').toString();
    }

    private static String lineJson() {
        List<Customer> all = line.snapshot();
        StringBuilder sb = new StringBuilder("{\"line\":[");
        for (int i = 0; i < all.size(); i++) {
            Customer c = all.get(i);
            if (i > 0) sb.append(',');
            sb.append("{\"token\":").append(c.token).append(",\"name\":").append(Json.quote(c.name))
              .append(",\"time\":").append(Json.quote(c.joinedAt)).append('}');
        }
        Customer s = line.getLastServed();
        sb.append("],\"waiting\":").append(all.size()).append(",\"serving\":");
        if (s == null) sb.append("null");
        else sb.append("{\"token\":").append(s.token).append(",\"name\":").append(Json.quote(s.name)).append('}');
        return sb.append('}').toString();
    }

    private static void mutation(HttpExchange ex, String op, String detail, String message) throws IOException {
        send(ex, 200, "{\"ok\":true,\"message\":" + Json.quote(message)
                + ",\"op\":" + Json.quote(op) + ",\"detail\":" + Json.quote(detail)
                + ",\"enq\":" + inv.getEnqCount() + ",\"deq\":" + inv.getDeqCount() + "}");
    }

    private static void save() { Storage.save(inv.snapshot()); }

    // ------------------------------------------------------------ http helpers
    private static int idFrom(String path) {
        try {
            return Integer.parseInt(path.substring(path.lastIndexOf('/') + 1));
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Invalid item.");
        }
    }

    private static String body(HttpExchange ex) throws IOException {
        try (InputStream in = ex.getRequestBody()) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static void error(HttpExchange ex, int code, String msg) throws IOException {
        send(ex, code, "{\"ok\":false,\"error\":" + Json.quote(msg) + "}");
    }

    private static void send(HttpExchange ex, int code, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        ex.sendResponseHeaders(code, bytes.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(bytes);
        }
    }
}
