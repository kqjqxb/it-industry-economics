namespace Availability;

public record WorkingHours(int Weekday, TimeOnly StartTime, TimeOnly EndTime);

public enum ExceptionType { Block, DayOff, ExtraHours }

public record AvailabilityException(ExceptionType Type, Interval Interval);

public record SlotsInput(
    TimeZoneInfo Timezone, DateTime From, DateTime To, DateTime Now,
    IReadOnlyList<WorkingHours> WorkingHours, IReadOnlyList<AvailabilityException> Exceptions,
    IReadOnlyList<Interval> Busy,
    int DurationMin, int BufferAfterMin, int SlotStepMin, int MinNoticeMin, int HorizonDays);

// Розрахунок вільних слотів для онлайн-запису. Чиста функція без БД і годинника.
public static class Slots
{
    // Робочі інтервали навколо локальної дати: тижневий шаблон дати та сусідніх
    // днів плюс додаткові години (extra_hours) у цьому вікні, об'єднані.
    public static List<Interval> WorkingIntervals(
        DateOnly date, TimeZoneInfo zone, IEnumerable<WorkingHours> workingHours,
        IEnumerable<Interval> extraHours)
    {
        var intervals = new List<Interval>();

        foreach (var day in new[] { date.AddDays(-1), date, date.AddDays(1) })
        {
            var weekday = Zoned.WeekdayOf(day);
            foreach (var hours in workingHours.Where(h => h.Weekday == weekday))
            {
                var start = Zoned.WallTimeToUtc(day, hours.StartTime, zone);
                var end = Zoned.WallTimeToUtc(day, hours.EndTime, zone);
                if (start < end) intervals.Add(new Interval(start, end));
            }
        }

        var window = new Interval(
            Zoned.WallTimeToUtc(date.AddDays(-1), TimeOnly.MinValue, zone),
            Zoned.WallTimeToUtc(date.AddDays(2), TimeOnly.MinValue, zone));
        intervals.AddRange(extraHours.Where(extra => Intervals.Overlaps(extra, window)));

        return Intervals.Merge(intervals);
    }

    public static List<Interval> GetFreeSlots(SlotsInput input)
    {
        var duration = TimeSpan.FromMinutes(input.DurationMin);
        var occupied = duration + TimeSpan.FromMinutes(input.BufferAfterMin);
        var step = TimeSpan.FromMinutes(input.SlotStepMin);
        if (duration <= TimeSpan.Zero || step <= TimeSpan.Zero || input.From >= input.To) return [];

        var earliest = input.Now.AddMinutes(input.MinNoticeMin);
        var latest = input.Now.AddDays(input.HorizonDays);

        var extraHours = input.Exceptions
            .Where(e => e.Type == ExceptionType.ExtraHours).Select(e => e.Interval).ToList();
        var closed = input.Exceptions
            .Where(e => e.Type != ExceptionType.ExtraHours).Select(e => e.Interval).ToList();

        var zone = input.Timezone;
        var slots = new List<Interval>();
        var lastDate = Zoned.LocalDateOf(input.To, zone);

        var firstDate = Zoned.LocalDateOf(input.From, zone);
        for (var date = firstDate; date <= lastDate; date = date.AddDays(1))
        {
            foreach (var interval in WorkingIntervals(date, zone, input.WorkingHours, extraHours))
            {
                // Сітка прив'язана до початку робочого інтервалу; блоки й записи її не зсувають.
                for (var start = interval.Start; start + duration <= interval.End; start += step)
                {
                    if (start < input.From || start >= input.To) continue;
                    if (start < earliest || start > latest) continue;
                    // Кожен початок видається один раз – своєю локальною датою.
                    if (Zoned.LocalDateOf(start, zone) != date) continue;

                    var service = new Interval(start, start + duration);
                    if (closed.Any(c => Intervals.Overlaps(c, service))) continue;

                    // Буфер має бути вільним від записів, але може виходити за робочий інтервал.
                    var busyCheck = new Interval(start, start + occupied);
                    if (input.Busy.Any(b => Intervals.Overlaps(b, busyCheck))) continue;

                    slots.Add(service);
                }
            }
        }

        return slots.OrderBy(s => s.Start).ToList();
    }
}
