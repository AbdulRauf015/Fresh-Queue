/** One recorded sale (kept in the sales-history queue). */
public class SaleRecord {
    public final String time;      // yyyy-MM-dd HH:mm
    public final String itemName;
    public final int quantity;
    public final double amount;    // total money for this sale

    public SaleRecord(String time, String itemName, int quantity, double amount) {
        this.time = time;
        this.itemName = itemName;
        this.quantity = quantity;
        this.amount = amount;
    }
}
