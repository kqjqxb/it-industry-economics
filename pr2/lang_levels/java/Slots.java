import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

// Розрахунок вільних слотів для онлайн-запису. Чиста функція без БД і годинника.
public final class Slots {
    private Slots() {
    }

    public record WorkingHours(int weekday, LocalTime startTime, LocalTime endTime) {
    }

    public enum ExceptionType { BLOCK, DAY_OFF, EXTRA_HOURS }

    public record AvailabilityException(ExceptionType type, Interval interval) {
    }

    public record Input(
            ZoneId timezone, Instant from, Instant to, Instant now,
            List<WorkingHours> workingHours, List<AvailabilityException> exceptions,
            List<Interval> busy, int durationMin, int bufferAfterMin, int slotStepMin,
            int minNoticeMin, int horizonDays) {
    }

    // Робочі інтервали навколо локальної дати: тижневий шаблон дати та сусідніх
    // днів плюс додаткові години (extra_hours) у цьому вікні, об'єднані.
    public static List<Interval> workingIntervals(
            LocalDate date, ZoneId zone, List<WorkingHours> workingHours,
            List<Interval> extraHours) {
        List<Interval> intervals = new ArrayList<>();

        for (LocalDate day : List.of(date.minusDays(1), date, date.plusDays(1))) {
            int weekday = Zoned.weekdayOf(day);
            for (WorkingHours hours : workingHours) {
                if (hours.weekday() != weekday) continue;
                Instant start = Zoned.wallTimeToUtc(day, hours.startTime(), zone);
                Instant end = Zoned.wallTimeToUtc(day, hours.endTime(), zone);
                if (start.isBefore(end)) intervals.add(new Interval(start, end));
            }
        }

        Interval window = new Interval(
                Zoned.wallTimeToUtc(date.minusDays(1), LocalTime.MIDNIGHT, zone),
                Zoned.wallTimeToUtc(date.plusDays(2), LocalTime.MIDNIGHT, zone));
        for (Interval extra : extraHours) {
            if (Intervals.overlaps(extra, window)) intervals.add(extra);
        }
        return Intervals.merge(intervals);
    }

    public static List<Interval> getFreeSlots(Input input) {
        Duration duration = Duration.ofMinutes(input.durationMin());
        Duration occupied = duration.plusMinutes(input.bufferAfterMin());
        Duration step = Duration.ofMinutes(input.slotStepMin());
        if (duration.isNegative() || duration.isZero() || step.isNegative() || step.isZero()
                || !input.from().isBefore(input.to())) {
            return List.of();
        }

        Instant earliest = input.now().plus(Duration.ofMinutes(input.minNoticeMin()));
        Instant latest = input.now().plus(Duration.ofDays(input.horizonDays()));

        List<Interval> extraHours = input.exceptions().stream()
                .filter(e -> e.type() == ExceptionType.EXTRA_HOURS)
                .map(AvailabilityException::interval).toList();
        List<Interval> closed = input.exceptions().stream()
                .filter(e -> e.type() != ExceptionType.EXTRA_HOURS)
                .map(AvailabilityException::interval).toList();

        ZoneId zone = input.timezone();
        List<Interval> slots = new ArrayList<>();
        LocalDate lastDate = Zoned.localDateOf(input.to(), zone);

        for (LocalDate date = Zoned.localDateOf(input.from(), zone); !date.isAfter(lastDate);
                date = date.plusDays(1)) {
            var intervals = workingIntervals(date, zone, input.workingHours(), extraHours);
            for (Interval interval : intervals) {
                // Сітка прив'язана до початку робочого інтервалу; блоки й записи її не зсувають.
                Instant end = interval.end();
                for (Instant start = interval.start(); !start.plus(duration).isAfter(end);
                        start = start.plus(step)) {
                    if (start.isBefore(input.from()) || !start.isBefore(input.to())) continue;
                    if (start.isBefore(earliest) || start.isAfter(latest)) continue;
                    // Кожен початок видається один раз – своєю локальною датою.
                    if (!Zoned.localDateOf(start, zone).equals(date)) continue;

                    Interval service = new Interval(start, start.plus(duration));
                    if (closed.stream().anyMatch(c -> Intervals.overlaps(c, service))) continue;

                    // Буфер має бути вільним від записів, але може виходити за робочий інтервал.
                    Interval busyCheck = new Interval(start, start.plus(occupied));
                    if (input.busy().stream().anyMatch(b -> Intervals.overlaps(b, busyCheck))) {
                        continue;
                    }

                    slots.add(service);
                }
            }
        }

        slots.sort(Comparator.comparing(Interval::start));
        return slots;
    }
}
