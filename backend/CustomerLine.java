import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/** The billing-counter line: the classic real-life queue. Customers are served in the order they arrive. */
public class CustomerLine {
    private final LinkedQueue<Customer> queue = new LinkedQueue<>();
    private int nextToken = 1;
    private Customer lastServed;

    /** A customer joins the line: enqueue at the rear. */
    public Customer join(String name) {
        String n = name == null || name.isBlank() ? "Customer " + nextToken : name.trim();
        Customer c = new Customer(nextToken++, n, LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm")));
        queue.enqueue(c);
        return c;
    }

    /** The counter calls the next customer: dequeue from the front. Returns null if nobody is waiting. */
    public Customer serveNext() {
        Customer c = queue.dequeue();
        if (c != null) lastServed = c;
        return c;
    }

    public Customer peek() { return queue.peek(); }
    public Customer getLastServed() { return lastServed; }
    public int size() { return queue.size(); }

    /** Everybody waiting, front to rear (queue rotated once, order preserved). */
    public List<Customer> snapshot() {
        List<Customer> list = new ArrayList<>();
        int n = queue.size();
        for (int i = 0; i < n; i++) {
            Customer c = queue.dequeue();
            list.add(c);
            queue.enqueue(c);
        }
        return list;
    }
}
