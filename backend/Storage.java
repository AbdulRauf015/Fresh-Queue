import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/** Saves/loads the queue (front to rear) in data/inventory_data.tsv so stock survives restarts. */
public final class Storage {
    private Storage() {}
    private static final Path FILE = Paths.get("data", "inventory_data.tsv");
    private static final Path SALES_FILE = Paths.get("data", "sales_data.tsv");

    private static String clean(String s) { return s.replace('\t', ' ').replace('\n', ' ').replace('\r', ' '); }

    public static void save(List<Product> items) {
        List<String> lines = new ArrayList<>();
        for (Product p : items) {
            lines.add(String.join("\t", String.valueOf(p.getId()), clean(p.getName()), clean(p.getCategory()),
                    String.valueOf(p.getQuantity()), String.valueOf(p.getPrice()), p.getExpiryDate()));
        }
        try {
            Files.createDirectories(FILE.getParent());
            Files.write(FILE, lines, StandardCharsets.UTF_8);
        } catch (IOException ignored) { }
    }

    public static List<Product> load() {
        List<Product> list = new ArrayList<>();
        if (!Files.exists(FILE)) return list;
        try {
            for (String line : Files.readAllLines(FILE, StandardCharsets.UTF_8)) {
                String[] f = line.split("\t");
                if (f.length < 6) continue;
                list.add(new Product(Integer.parseInt(f[0]), f[1], f[2], Integer.parseInt(f[3]),
                        Double.parseDouble(f[4]), f[5]));
            }
        } catch (Exception e) {
            return new ArrayList<>();
        }
        return list;
    }

    public static void saveSales(List<SaleRecord> sales) {
        List<String> lines = new ArrayList<>();
        for (SaleRecord r : sales) {
            lines.add(String.join("\t", r.time, clean(r.itemName), String.valueOf(r.quantity), String.valueOf(r.amount)));
        }
        try {
            Files.createDirectories(SALES_FILE.getParent());
            Files.write(SALES_FILE, lines, StandardCharsets.UTF_8);
        } catch (IOException ignored) { }
    }

    public static List<SaleRecord> loadSales() {
        List<SaleRecord> list = new ArrayList<>();
        if (!Files.exists(SALES_FILE)) return list;
        try {
            for (String line : Files.readAllLines(SALES_FILE, StandardCharsets.UTF_8)) {
                String[] f = line.split("\t");
                if (f.length < 4) continue;
                list.add(new SaleRecord(f[0], f[1], Integer.parseInt(f[2]), Double.parseDouble(f[3])));
            }
        } catch (Exception e) {
            return new ArrayList<>();
        }
        return list;
    }

    /** Practice data (dates are relative to today). */
    public static List<Product> sample(int firstId) {
        LocalDate t = LocalDate.now();
        List<Product> l = new ArrayList<>();
        l.add(new Product(firstId, "Fresh Milk 1L", "Dairy", 60, 290, t.plusDays(2).toString()));
        l.add(new Product(firstId + 1, "Bread Loaf", "Bakery", 35, 150, t.plusDays(3).toString()));
        l.add(new Product(firstId + 2, "Yogurt 500g", "Dairy", 48, 210, t.plusDays(6).toString()));
        l.add(new Product(firstId + 3, "Orange Juice", "Drinks", 40, 320, t.plusDays(45).toString()));
        l.add(new Product(firstId + 4, "Basmati Rice 5kg", "Grains", 90, 1650, t.plusDays(240).toString()));
        return l;
    }
}
