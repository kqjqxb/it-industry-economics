import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

// Тестовий драйвер: читає scenarios.txt і друкує вільні слоти кожного сценарію.
public final class Main {
    public static void main(String[] args) throws IOException {
        String path = args.length > 0 ? args[0] : "../scenarios.txt";
        String name = "";
        ZoneId zone = null;
        Instant from = null, to = null, now = null;
        int[] params = new int[5];
        List<Slots.WorkingHours> hours = new ArrayList<>();
        List<Slots.AvailabilityException> exceptions = new ArrayList<>();
        List<Interval> busy = new ArrayList<>();

        for (String raw : Files.readAllLines(Path.of(path))) {
            String line = raw.strip();
            if (line.isEmpty() || line.startsWith("#")) continue;
            String[] v = line.split("\\s+");
            switch (v[0]) {
                case "scenario" -> {
                    name = v[1];
                    hours = new ArrayList<>();
                    exceptions = new ArrayList<>();
                    busy = new ArrayList<>();
                }
                case "timezone" -> zone = ZoneId.of(v[1]);
                case "from" -> from = Instant.parse(v[1]);
                case "to" -> to = Instant.parse(v[1]);
                case "now" -> now = Instant.parse(v[1]);
                case "params" -> {
                    for (int i = 0; i < 5; i++) params[i] = Integer.parseInt(v[i + 1]);
                }
                case "hours" -> hours.add(new Slots.WorkingHours(
                        Integer.parseInt(v[1]), LocalTime.parse(v[2]), LocalTime.parse(v[3])));
                case "exception" -> exceptions.add(new Slots.AvailabilityException(
                        Slots.ExceptionType.valueOf(v[1].toUpperCase(Locale.ROOT)),
                        new Interval(Instant.parse(v[2]), Instant.parse(v[3]))));
                case "busy" -> busy.add(new Interval(Instant.parse(v[1]), Instant.parse(v[2])));
                case "end" -> {
                    var input = new Slots.Input(zone, from, to, now, hours, exceptions, busy,
                            params[0], params[1], params[2], params[3], params[4]);
                    List<Interval> slots = Slots.getFreeSlots(input);
                    System.out.println(name + ": " + slots.size());
                    for (Interval slot : slots) {
                        System.out.println("  " + iso(slot.start()) + " " + iso(slot.end()));
                    }
                }
                default -> throw new IllegalArgumentException("Невідомий рядок: " + line);
            }
        }
    }

    private static String iso(Instant instant) {
        return instant.truncatedTo(ChronoUnit.MINUTES).toString().replace(":00Z", "Z");
    }
}
