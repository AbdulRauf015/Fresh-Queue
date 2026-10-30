/** A customer waiting in the billing-counter line. */
public class Customer {
    public final int token;
    public final String name;
    public final String joinedAt; // HH:mm

    public Customer(int token, String name, String joinedAt) {
        this.token = token;
        this.name = name;
        this.joinedAt = joinedAt;
    }
}
