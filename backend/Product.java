import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

/** One stock batch (e.g. a delivery of milk) stored in the inventory queue. */
public class Product {
    private final int id;
    private String name;
    private String category;
    private int quantity;
    private double price;
    private String expiryDate; // yyyy-MM-dd

    public Product(int id, String name, String category, int quantity, double price, String expiryDate) {
        this.id = id;
        this.name = name;
        this.category = category;
        this.quantity = quantity;
        this.price = price;
        this.expiryDate = expiryDate;
    }

    public int getId() { return id; }
    public String getName() { return name; }
    public String getCategory() { return category; }
    public int getQuantity() { return quantity; }
    public double getPrice() { return price; }
    public String getExpiryDate() { return expiryDate; }

    public void setName(String name) { this.name = name; }
    public void setCategory(String category) { this.category = category; }
    public void setQuantity(int quantity) { this.quantity = quantity; }
    public void setPrice(double price) { this.price = price; }
    public void setExpiryDate(String expiryDate) { this.expiryDate = expiryDate; }

    /** Stock at or below this many pieces is "low". */
    public static final int LOW_STOCK_LIMIT = 10;

    public boolean isLow() { return quantity <= LOW_STOCK_LIMIT; }

    /** Days from today until expiry (negative = already expired). */
    public long daysLeft() {
        try {
            return ChronoUnit.DAYS.between(LocalDate.now(), LocalDate.parse(expiryDate));
        } catch (Exception e) {
            return Long.MAX_VALUE;
        }
    }
}
