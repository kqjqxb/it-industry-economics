namespace Availability;

// Перетворення локального часу закладу (часовий пояс IANA) в UTC і навпаки.
public static class Zoned
{
    // Локальні дата й час у поясі як момент UTC. Неіснуючий час (перехід на
    // літній час) береться зі зсувом до переходу, а повторюваний (перехід на
    // зимовий) – з пізнішим, меншим зсувом, як у Postgres.
    public static DateTime WallTimeToUtc(DateOnly date, TimeOnly time, TimeZoneInfo zone)
    {
        var wall = date.ToDateTime(time, DateTimeKind.Unspecified);
        TimeSpan offset;
        if (zone.IsAmbiguousTime(wall)) offset = zone.GetAmbiguousTimeOffsets(wall).Min();
        else if (zone.IsInvalidTime(wall)) offset = zone.GetUtcOffset(wall.AddDays(-1));
        else offset = zone.GetUtcOffset(wall);
        return DateTime.SpecifyKind(wall - offset, DateTimeKind.Utc);
    }

    public static DateOnly LocalDateOf(DateTime instant, TimeZoneInfo zone) =>
        DateOnly.FromDateTime(TimeZoneInfo.ConvertTimeFromUtc(instant, zone));

    public static TimeOnly LocalTimeOf(DateTime instant, TimeZoneInfo zone) =>
        TimeOnly.FromDateTime(TimeZoneInfo.ConvertTimeFromUtc(instant, zone));

    // Кінець локальної доби – наступна локальна північ.
    public static DateTime EndOfDay(DateOnly date, TimeZoneInfo zone) =>
        WallTimeToUtc(date.AddDays(1), TimeOnly.MinValue, zone);

    // 0 = неділя, як у working_hours.weekday.
    public static int WeekdayOf(DateOnly date) => (int)date.DayOfWeek;
}
