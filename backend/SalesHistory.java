import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * The last 50 sales, kept in a BOUNDED QUEUE: when the 51st sale arrives the oldest
 * one is dequeued first, then the new one is enqueued (FIFO).
 */
public class SalesHistory {
    public static final int CAPACITY = 50;
    private final LinkedQueue<SaleRecord> queue = new LinkedQueue<>();

    public void record(SaleRecord r) {
        if (queue.size() >= CAPACITY) {
            queue.dequeue();
        }
        queue.enqueue(r);
    }

    /** Oldest first (queue order). Rotates the queue once; order is preserved. */
    public List<SaleRecord> snapshot() {
        List<SaleRecord> list = new ArrayList<>();
        int n = queue.size();
        for (int i = 0; i < n; i++) {
            SaleRecord r = queue.dequeue();
            list.add(r);
            queue.enqueue(r);
        }
        return list;
    }

    public double todayAmount() {
        String today = LocalDate.now().toString();
        double sum = 0;
        for (SaleRecord r : snapshot()) if (r.time.startsWith(today)) sum += r.amount;
        return sum;
    }

    public int todayPieces() {
        String today = LocalDate.now().toString();
        int sum = 0;
        for (SaleRecord r : snapshot()) if (r.time.startsWith(today)) sum += r.quantity;
        return sum;
    }
}
