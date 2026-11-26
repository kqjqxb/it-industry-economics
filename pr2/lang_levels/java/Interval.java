import java.time.Instant;

// Напіввідкритий інтервал часу [start, end) у UTC.
public record Interval(Instant start, Instant end) {
}
