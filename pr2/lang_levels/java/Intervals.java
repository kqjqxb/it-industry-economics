import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

// Операції над інтервалами часу.
public final class Intervals {
    private Intervals() {
    }

    public static boolean overlaps(Interval a, Interval b) {
        return a.start().isBefore(b.end()) && b.start().isBefore(a.end());
    }

    public static boolean contains(Interval outer, Interval inner) {
        return !inner.start().isBefore(outer.start()) && !outer.end().isBefore(inner.end());
    }

    // Об'єднує інтервали, що перетинаються або торкаються, і відкидає порожні.
    public static List<Interval> merge(List<Interval> intervals) {
        List<Interval> sorted = intervals.stream()
                .filter(i -> i.start().isBefore(i.end()))
                .sorted(Comparator.comparing(Interval::start))
                .toList();

        List<Interval> merged = new ArrayList<>();
        for (Interval interval : sorted) {
            int lastIndex = merged.size() - 1;
            if (lastIndex >= 0 && !interval.start().isAfter(merged.get(lastIndex).end())) {
                Interval last = merged.get(lastIndex);
                if (interval.end().isAfter(last.end())) {
                    merged.set(lastIndex, new Interval(last.start(), interval.end()));
                }
            } else {
                merged.add(interval);
            }
        }
        return merged;
    }

    // Частини base, не покриті жодним з cuts.
    public static List<Interval> subtract(List<Interval> base, List<Interval> cuts) {
        List<Interval> mergedCuts = merge(cuts);
        List<Interval> result = new ArrayList<>();

        for (Interval interval : merge(base)) {
            Instant cursor = interval.start();
            for (Interval cut : mergedCuts) {
                if (!cut.end().isAfter(cursor)) continue;
                if (!cut.start().isBefore(interval.end())) break;
                if (cut.start().isAfter(cursor)) result.add(new Interval(cursor, cut.start()));
                if (cut.end().isAfter(cursor)) cursor = cut.end();
            }
            if (cursor.isBefore(interval.end())) result.add(new Interval(cursor, interval.end()));
        }
        return result;
    }
}
