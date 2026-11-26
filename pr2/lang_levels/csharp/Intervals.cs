namespace Availability;

// Напіввідкритий інтервал часу [Start, End) у UTC.
public readonly record struct Interval(DateTime Start, DateTime End);

public static class Intervals
{
    public static bool Overlaps(Interval a, Interval b) => a.Start < b.End && b.Start < a.End;

    public static bool Contains(Interval outer, Interval inner) =>
        outer.Start <= inner.Start && inner.End <= outer.End;

    // Об'єднує інтервали, що перетинаються або торкаються, і відкидає порожні.
    public static List<Interval> Merge(IEnumerable<Interval> intervals)
    {
        var merged = new List<Interval>();
        foreach (var interval in intervals.Where(i => i.Start < i.End).OrderBy(i => i.Start))
        {
            if (merged.Count > 0 && interval.Start <= merged[^1].End)
            {
                var last = merged[^1];
                if (interval.End > last.End) merged[^1] = last with { End = interval.End };
            }
            else
            {
                merged.Add(interval);
            }
        }
        return merged;
    }

    // Частини baseIntervals, не покриті жодним з cuts.
    public static List<Interval> Subtract(
        IEnumerable<Interval> baseIntervals, IEnumerable<Interval> cuts)
    {
        var mergedCuts = Merge(cuts);
        var result = new List<Interval>();

        foreach (var interval in Merge(baseIntervals))
        {
            var cursor = interval.Start;
            foreach (var cut in mergedCuts)
            {
                if (cut.End <= cursor) continue;
                if (cut.Start >= interval.End) break;
                if (cut.Start > cursor) result.Add(new Interval(cursor, cut.Start));
                if (cut.End > cursor) cursor = cut.End;
            }
            if (cursor < interval.End) result.Add(new Interval(cursor, interval.End));
        }
        return result;
    }
}
