import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Stock operations, built ONLY on the queue's enqueue() / dequeue() / peek() / size().
 *
 * A queue has no random access, so to reach a record in the middle we use the
 * "rotate" technique: dequeue every product exactly once and enqueue it back,
 * which restores the original order. The number of enqueue/dequeue calls of the
 * last operation is available via getEnqCount() / getDeqCount().
 */
public class InventoryManager {
    private final LinkedQueue<Product> queue = new LinkedQueue<>();
    private int enqCount;
    private int deqCount;
    private boolean quiet; // when true, calls are not counted (used for screen refresh)

    // ---- result of a sale -------------------------------------------------
    public static class SalePart {
        public final int id;
        public final int took;
        public final boolean finished;
        public final double price;

        SalePart(int id, int took, boolean finished, double price) {
            this.id = id;
            this.took = took;
            this.finished = finished;
            this.price = price;
        }
    }

    public static class SaleResult {
        public String error;          // null when the sale worked
        public String itemName;
        public double amount;
        public final List<SalePart> parts = new ArrayList<>();
    }

    // ---- counting helpers -------------------------------------------------
    private void resetOps() { enqCount = 0; deqCount = 0; }

    private void enq(Product p) {
        queue.enqueue(p);
        if (!quiet) enqCount++;
    }

    private Product deq() {
        Product p = queue.dequeue();
        if (!quiet && p != null) deqCount++;
        return p;
    }

    public int getEnqCount() { return enqCount; }
    public int getDeqCount() { return deqCount; }
    public int size() { return queue.size(); }

    // ---------- CREATE ----------
    /** Adds a new batch at the rear. Returns false if the ID already exists. */
    public boolean create(Product p) {
        resetOps();
        if (rotateFind(p.getId()) != null) {
            return false;
        }
        enq(p);
        return true;
    }

    /** Fast loading (start-up, tests): enqueue everything at the rear, no duplicate check. */
    public void bulkLoad(List<Product> products) {
        for (Product p : products) enq(p);
    }

    // ---------- READ ----------
    /** All products from front to rear (order preserved). Not counted as an operation. */
    public List<Product> snapshot() {
        quiet = true;
        List<Product> list = new ArrayList<>();
        int n = queue.size();
        for (int i = 0; i < n; i++) {
            Product p = deq();
            list.add(p);
            enq(p);
        }
        quiet = false;
        return list;
    }

    /** Finds a product by ID (full rotation, order preserved). Returns null if not found. */
    public Product find(int id) {
        resetOps();
        return rotateFind(id);
    }

    /** Products whose name or category contains the text (full rotation, order preserved). */
    public List<Product> search(String text) {
        resetOps();
        String q = text.trim().toLowerCase();
        List<Product> hits = new ArrayList<>();
        int n = queue.size();
        for (int i = 0; i < n; i++) {
            Product p = deq();
            if (p.getName().toLowerCase().contains(q) || p.getCategory().toLowerCase().contains(q)) {
                hits.add(p);
            }
            enq(p);
        }
        return hits;
    }

    /** The next batch to be sold (front) without removing it. */
    public Product peekNext() {
        return queue.peek();
    }

    /** Next free ID = highest ID in use + 1. */
    public int nextId() {
        int max = 100;
        for (Product p : snapshot()) {
            if (p.getId() > max) max = p.getId();
        }
        return max + 1;
    }

    /** Item names that can be sold right now (not expired) with the pieces available. */
    public Map<String, Integer> availableByName() {
        Map<String, Integer> map = new LinkedHashMap<>();
        for (Product p : snapshot()) {
            if (p.daysLeft() >= 0 && p.getQuantity() > 0) {
                map.merge(p.getName(), p.getQuantity(), Integer::sum);
            }
        }
        return map;
    }

    // ---------- UPDATE ----------
    public boolean update(int id, String name, String category, int qty, double price, String expiry) {
        resetOps();
        boolean updated = false;
        int n = queue.size();
        for (int i = 0; i < n; i++) {
            Product p = deq();
            if (p.getId() == id) {
                p.setName(name);
                p.setCategory(category);
                p.setQuantity(qty);
                p.setPrice(price);
                p.setExpiryDate(expiry);
                updated = true;
            }
            enq(p);
        }
        return updated;
    }

    // ---------- SELL (FIFO) ----------
    /**
     * Sells {@code qty} pieces of an item, always taking from the OLDEST batch first.
     * Pass 1 rotates the queue to check that enough sellable stock exists.
     * Pass 2 rotates again and takes pieces batch by batch from the front side;
     * a batch that reaches zero is simply not enqueued back (it is finished).
     * Expired batches are never sold.
     */
    public SaleResult sell(String name, int qty) {
        resetOps();
        SaleResult res = new SaleResult();
        String key = name.trim().toLowerCase();

        int available = 0;
        int n = queue.size();
        for (int i = 0; i < n; i++) {
            Product p = deq();
            if (p.getName().toLowerCase().equals(key) && p.daysLeft() >= 0) {
                available += p.getQuantity();
                res.itemName = p.getName();
            }
            enq(p);
        }
        if (available == 0) {
            res.error = "'" + name + "' is not in stock (or only expired stock is left).";
            return res;
        }
        if (qty > available) {
            res.error = "Only " + available + " piece(s) of '" + res.itemName + "' can be sold. You asked for " + qty + ".";
            return res;
        }

        int remaining = qty;
        for (int i = 0; i < n; i++) {
            Product p = deq();
            if (remaining > 0 && p.getName().toLowerCase().equals(key) && p.daysLeft() >= 0) {
                int take = Math.min(p.getQuantity(), remaining);
                p.setQuantity(p.getQuantity() - take);
                remaining -= take;
                res.amount += take * p.getPrice();
                boolean finished = p.getQuantity() == 0;
                res.parts.add(new SalePart(p.getId(), take, finished, p.getPrice()));
                if (finished) {
                    continue; // empty batch leaves the queue
                }
            }
            enq(p);
        }
        return res;
    }

    // ---------- DELETE ----------
    /** FIFO delete: removes and returns the oldest batch (front). O(1) */
    public Product dequeueFront() {
        resetOps();
        return deq();
    }

    /** Delete a specific product: rotate the queue and do not enqueue that one back. */
    public Product deleteById(int id) {
        resetOps();
        Product removed = null;
        int n = queue.size();
        for (int i = 0; i < n; i++) {
            Product p = deq();
            if (p.getId() == id && removed == null) {
                removed = p;
            } else {
                enq(p);
            }
        }
        return removed;
    }

    /** Removes every expired batch in one rotation. Returns the removed products. */
    public List<Product> removeExpired() {
        resetOps();
        List<Product> removed = new ArrayList<>();
        int n = queue.size();
        for (int i = 0; i < n; i++) {
            Product p = deq();
            if (p.daysLeft() < 0) {
                removed.add(p);
            } else {
                enq(p);
            }
        }
        return removed;
    }

    private Product rotateFind(int id) {
        Product found = null;
        int n = queue.size();
        for (int i = 0; i < n; i++) {
            Product p = deq();
            if (p.getId() == id) found = p;
            enq(p);
        }
        return found;
    }
}
