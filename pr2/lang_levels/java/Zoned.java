import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;

// Перетворення локального часу закладу (часовий пояс IANA) в UTC і навпаки.
public final class Zoned {
    private Zoned() {
    }

    // Локальні дата й час у поясі як момент UTC. Неіснуючий час (перехід на
    // літній час) зсувається вперед на величину переходу, а повторюваний
    // (перехід на зимовий) береться з пізнішим зсувом – як у Postgres.
    public static Instant wallTimeToUtc(LocalDate date, LocalTime time, ZoneId zone) {
        return LocalDateTime.of(date, time).atZone(zone).withLaterOffsetAtOverlap().toInstant();
    }

    public static LocalDate localDateOf(Instant instant, ZoneId zone) {
        return instant.atZone(zone).toLocalDate();
    }

    public static LocalTime localTimeOf(Instant instant, ZoneId zone) {
        return instant.atZone(zone).toLocalTime();
    }

    // Кінець локальної доби – наступна локальна північ.
    public static Instant endOfDay(LocalDate date, ZoneId zone) {
        return wallTimeToUtc(date.plusDays(1), LocalTime.MIDNIGHT, zone);
    }

    // 0 = неділя, як у working_hours.weekday.
    public static int weekdayOf(LocalDate date) {
        return date.getDayOfWeek().getValue() % 7;
    }
}
