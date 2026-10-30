import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Speed test for the report ("Analysis & Results").
 * Runs on a SEPARATE temporary queue, never on the real stock.
 * Times (microseconds per operation) are measured for queues of different sizes:
 *   O(1) operations: enqueue, dequeue, peek
 *   O(n) operations: search, edit, remove a chosen item (each must rotate the whole queue)
 */
public final class Benchmark {
    private Benchmark() {}

    private static volatile long sink; // stops the JVM from optimising the loops away

    public static String run(int[] sizes) {
        for (int i = 0; i < 5; i++) measure(1000); // warm-up so the JVM has compiled everything; results thrown away
        StringBuilder sb = new StringBuilder("{\"results\":[");
        for (int i = 0; i < sizes.length; i++) {
            double[] r = measure(sizes[i]);
            // measure 3 times and keep the best (smallest) time: removes noise from garbage collection etc.
            for (int k = 0; k < 2; k++) {
                double[] again = measure(sizes[i]);
                for (int j = 0; j < r.length; j++) r[j] = Math.min(r[j], again[j]);
            }
            if (i > 0) sb.append(',');
            sb.append(String.format(Locale.ROOT,
                    "{\"n\":%d,\"enqueue\":%.5f,\"dequeue\":%.5f,\"peek\":%.5f,\"search\":%.4f,\"edit\":%.4f,\"remove\":%.4f}",
                    sizes[i], r[0], r[1], r[2], r[3], r[4], r[5]));
        }
        return sb.append("]}").toString();
    }

    /** Returns microseconds per operation: {enqueue, dequeue, peek, search, edit, remove}. */
    private static double[] measure(int n) {
        List<Product> list = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            list.add(new Product(1000 + i, "Item " + i, "Test", 10, 100, "2030-01-01"));
        }

        // enqueue / dequeue: repeat on fresh queues until at least ~100,000 operations were timed
        int rounds = Math.max(1, 100000 / n);
        long enqNs = 0, deqNs = 0;
        LinkedQueue<Product> q = new LinkedQueue<>();
        for (int r = 0; r < rounds; r++) {
            q = new LinkedQueue<>();
            long t = System.nanoTime();
            for (Product p : list) q.enqueue(p);
            enqNs += System.nanoTime() - t;
            if (r < rounds - 1) { // keep the last queue full for the peek test
                t = System.nanoTime();
                for (int i = 0; i < n; i++) q.dequeue();
                deqNs += System.nanoTime() - t;
            }
        }
        double enq = enqNs / 1000.0 / ((double) n * rounds);

        int peeks = Math.max(n, 200000);
        long acc = 0;
        long t0 = System.nanoTime();
        for (int i = 0; i < peeks; i++) acc += sink + q.peek().getId(); // reading "sink" (volatile) stops the JVM from skipping the peek
        double peek = (System.nanoTime() - t0) / 1000.0 / peeks;
        sink = acc;

        t0 = System.nanoTime();
        for (int i = 0; i < n; i++) q.dequeue();
        deqNs += System.nanoTime() - t0;
        double deq = deqNs / 1000.0 / ((double) n * rounds);

        InventoryManager inv = new InventoryManager();
        inv.bulkLoad(list);
        int lastId = list.get(n - 1).getId(); // worst case: the item is at the very rear
        int reps = Math.max(5, 100000 / n);

        t0 = System.nanoTime();
        for (int i = 0; i < reps; i++) sink = inv.find(lastId).getId();
        double search = (System.nanoTime() - t0) / 1000.0 / reps;

        t0 = System.nanoTime();
        for (int i = 0; i < reps; i++) inv.update(lastId, "Item x", "Test", 11, 100, "2030-01-01");
        double edit = (System.nanoTime() - t0) / 1000.0 / reps;

        t0 = System.nanoTime();
        for (int i = 0; i < reps; i++) {
            Product p = inv.deleteById(lastId); // one full rotation
            List<Product> back = new ArrayList<>(1);
            back.add(p);
            inv.bulkLoad(back);                 // put it back at the rear: O(1)
        }
        double remove = (System.nanoTime() - t0) / 1000.0 / reps;

        return new double[]{enq, deq, peek, search, edit, remove};
    }
}
