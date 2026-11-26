// Тестовий драйвер: читає scenarios.txt і друкує вільні слоти кожного сценарію.
import { readFileSync } from "node:fs";

import type { Interval } from "./intervals";
import { type AvailabilityException, type GetFreeSlotsInput, getFreeSlots } from "./slots";

type Scenario = { name: string; input: GetFreeSlotsInput };

function parseScenarios(path: string): Scenario[] {
  const scenarios: Scenario[] = [];
  let name = "";
  let input = {} as GetFreeSlotsInput;
  let hours: GetFreeSlotsInput["workingHours"][number][] = [];
  let exceptions: AvailabilityException[] = [];
  let busy: Interval[] = [];

  for (const raw of readFileSync(path, "utf8").split("\n")) {
    const line = raw.trim();
    if (line === "" || line.startsWith("#")) continue;
    const [key, ...v] = line.split(/\s+/);
    if (key === "scenario") {
      name = v[0]!;
      input = {} as GetFreeSlotsInput;
      hours = [];
      exceptions = [];
      busy = [];
    } else if (key === "timezone") input.timezone = v[0]!;
    else if (key === "from") input.from = new Date(v[0]!);
    else if (key === "to") input.to = new Date(v[0]!);
    else if (key === "now") input.now = new Date(v[0]!);
    else if (key === "params") {
      const [duration, buffer, step, notice, horizon] = v.map(Number);
      Object.assign(input, {
        durationMin: duration,
        bufferAfterMin: buffer,
        slotStepMin: step,
        minNoticeMin: notice,
        horizonDays: horizon,
      });
    } else if (key === "hours") {
      hours.push({ weekday: Number(v[0]), startTime: v[1]!, endTime: v[2]! });
    } else if (key === "exception") {
      const type = v[0] as AvailabilityException["type"];
      exceptions.push({ type, start: new Date(v[1]!), end: new Date(v[2]!) });
    } else if (key === "busy") busy.push({ start: new Date(v[0]!), end: new Date(v[1]!) });
    else if (key === "end") {
      scenarios.push({ name, input: { ...input, workingHours: hours, exceptions, busy } });
    }
  }
  return scenarios;
}

const iso = (date: Date) => date.toISOString().slice(0, 16) + "Z";

for (const { name, input } of parseScenarios(process.argv[2] ?? "../scenarios.txt")) {
  const slots = getFreeSlots(input);
  console.log(`${name}: ${slots.length}`);
  for (const slot of slots) console.log(`  ${iso(slot.start)} ${iso(slot.end)}`);
}
