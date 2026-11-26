// Тестовий драйвер: читає scenarios.txt і друкує вільні слоти кожного сценарію.
using System.Globalization;
using Availability;

var path = args.Length > 0 ? args[0] : "../scenarios.txt";
var name = "";
TimeZoneInfo zone = TimeZoneInfo.Utc;
DateTime from = default, to = default, now = default;
var p = new int[5];
var hours = new List<WorkingHours>();
var exceptions = new List<AvailabilityException>();
var busy = new List<Interval>();

static DateTime Utc(string s) =>
    DateTime.Parse(s, CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal);
static string Iso(DateTime d) => d.ToString("yyyy-MM-ddTHH:mm'Z'", CultureInfo.InvariantCulture);

foreach (var raw in File.ReadLines(path))
{
    var line = raw.Trim();
    if (line.Length == 0 || line.StartsWith('#')) continue;
    var v = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
    switch (v[0])
    {
        case "scenario":
            name = v[1];
            hours = [];
            exceptions = [];
            busy = [];
            break;
        case "timezone": zone = TimeZoneInfo.FindSystemTimeZoneById(v[1]); break;
        case "from": from = Utc(v[1]); break;
        case "to": to = Utc(v[1]); break;
        case "now": now = Utc(v[1]); break;
        case "params":
            for (var i = 0; i < 5; i++) p[i] = int.Parse(v[i + 1]);
            break;
        case "hours":
            hours.Add(new WorkingHours(
                int.Parse(v[1]), TimeOnly.Parse(v[2]), TimeOnly.Parse(v[3])));
            break;
        case "exception":
            var type = v[1] switch
            {
                "block" => ExceptionType.Block,
                "day_off" => ExceptionType.DayOff,
                _ => ExceptionType.ExtraHours,
            };
            exceptions.Add(new AvailabilityException(type, new Interval(Utc(v[2]), Utc(v[3]))));
            break;
        case "busy": busy.Add(new Interval(Utc(v[1]), Utc(v[2]))); break;
        case "end":
            var input = new SlotsInput(
                zone, from, to, now, hours, exceptions, busy, p[0], p[1], p[2], p[3], p[4]);
            var slots = Slots.GetFreeSlots(input);
            Console.WriteLine($"{name}: {slots.Count}");
            foreach (var slot in slots) Console.WriteLine($"  {Iso(slot.Start)} {Iso(slot.End)}");
            break;
        default: throw new ArgumentException($"Невідомий рядок: {line}");
    }
}
