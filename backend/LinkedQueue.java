/**
 * Queue (FIFO) implemented from scratch using linked nodes. Generic, so the same
 * class is used for the stock (Product), the sales history (SaleRecord) and the
 * customer line (Customer).
 *
 * Only the standard queue operations are exposed: enqueue, dequeue, peek,
 * isEmpty and size. There is no random access, so FIFO is always preserved.
 */
public class LinkedQueue<T> {
    private Node<T> front; // dequeue happens here
    private Node<T> rear;  // enqueue happens here
    private int size;

    public LinkedQueue() {
        front = rear = null;
        size = 0;
    }

    /** Add an item at the REAR. O(1) */
    public void enqueue(T item) {
        Node<T> node = new Node<>(item);
        if (isEmpty()) {
            front = rear = node;
        } else {
            rear.next = node;
            rear = node;
        }
        size++;
    }

    /** Remove and return the item at the FRONT. O(1). Returns null if empty. */
    public T dequeue() {
        if (isEmpty()) {
            return null;
        }
        T item = front.data;
        front = front.next;
        if (front == null) {
            rear = null;
        }
        size--;
        return item;
    }

    /** Look at the FRONT item without removing it. O(1) */
    public T peek() {
        return isEmpty() ? null : front.data;
    }

    public boolean isEmpty() { return size == 0; }

    public int size() { return size; }
}
