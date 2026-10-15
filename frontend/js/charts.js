const HOUR_LABELS = [];
for (let hour = 0; hour < 24; hour++) {
    HOUR_LABELS.push(hour);
}

// the API sends one row per day type (weekday and weekend), this joins them into one row per key
function combineDayTypes(rows, keyName, valueNames, weightName = "trips") {
    const groups = {};

    rows.forEach(row => {
        const key = row[keyName];
        if (!groups[key]) {
            groups[key] = { weight: 0, trips: 0, sums: {} };
            valueNames.forEach(name => { groups[key].sums[name] = 0; });
        }

        const weight = Number(row[weightName]) || 0;
        groups[key].weight += weight;
        groups[key].trips += Number(row.trips) || 0;
        valueNames.forEach(name => {
            groups[key].sums[name] += (Number(row[name]) || 0) * weight;
        });
    });

    return Object.keys(groups).map(key => {
        const combined = { trips: groups[key].trips, weight: groups[key].weight };
        combined[keyName] = Number(key);
        valueNames.forEach(name => {
            combined[name] = groups[key].weight === 0 ? null : groups[key].sums[name] / groups[key].weight;
        });
        return combined;
    }).sort((a, b) => a[keyName] - b[keyName]);
}

function getValue(rows, keyName, valueName, key) {
    const row = rows.find(item => item[keyName] === key);
    return row ? row[valueName] : null;
}

// one small bar chart (one bar for every hour), the selected hour is orange
function drawBars(box, title, values, selectedHour, unit) {
    const set = document.createElement("div");
    set.className = "bar-set";

    const heading = document.createElement("h3");
    heading.textContent = title;
    set.appendChild(heading);

    const bars = document.createElement("div");
    bars.className = "bars";
    const labels = document.createElement("div");
    labels.className = "bar-labels";

    const numbers = values.filter(value => value !== null);
    const largest = numbers.length === 0 ? 1 : Math.max(...numbers);

    HOUR_LABELS.forEach((hour, index) => {
        const value = values[index];
        const bar = document.createElement("div");
        bar.className = "bar";
        if (selectedHour !== "all" && Number(selectedHour) === hour) {
            bar.classList.add("selected");
        }
        bar.style.height = value === null ? "0%" : `${Math.max(2, (value / largest) * 100)}%`;
        bar.title = `${hour}:00 - ${value === null ? "no data" : value.toFixed(2)} ${unit}`;
        bars.appendChild(bar);

        const label = document.createElement("span");
        label.textContent = hour % 3 === 0 ? hour : "";
        labels.appendChild(label);
    });

    set.appendChild(bars);
    set.appendChild(labels);
    box.appendChild(set);
}

function showChartNote(box, text) {
    const note = document.createElement("p");
    note.className = "help-text";
    note.textContent = text;
    box.appendChild(note);
}

function readDayType() {
    return document.querySelector("#day-type").value;
}

async function loadCharts(hour = "all", version = "cleaned") {
    const box = document.querySelector("#hourly-chart");

    try{
        const dayType = readDayType();
        box.replaceChildren();
        box.classList.add("loaded");

        if (version === "raw") {
            const rows = await getRawVsClean(dayType);
            const cleaned = combineDayTypes(rows, "hour", ["mean_speed_mph"], "trips");
            const raw = combineDayTypes(rows, "hour", ["raw_mean_speed_mph"], "raw_trips");

            drawBars(box, "Mean speed before cleaning (mph)", HOUR_LABELS.map(h => getValue(raw, "hour", "raw_mean_speed_mph", h)), hour, "mph");
            drawBars(box, "Mean speed after cleaning (mph)", HOUR_LABELS.map(h => getValue(cleaned, "hour", "mean_speed_mph", h)), hour, "mph");
            showChartNote(box, "Impossible trips (negative times, dates from 2001 to 2088, speeds above 80 mph) push the raw average up.");
            return;
        }

        const rows = combineDayTypes(await getHourProfile(dayType), "hour",
            ["median_min_per_mile", "median_speed_mph", "median_fare_per_min"]);

        drawBars(box, "Minutes per mile", HOUR_LABELS.map(h => getValue(rows, "hour", "median_min_per_mile", h)), hour, "min/mile");
        drawBars(box, "Median speed (mph)", HOUR_LABELS.map(h => getValue(rows, "hour", "median_speed_mph", h)), hour, "mph");
        drawBars(box, "Fare per minute ($)", HOUR_LABELS.map(h => getValue(rows, "hour", "median_fare_per_min", h)), hour, "$/min");
        showChartNote(box, "Medians, so a few extreme trips cannot move the bars. The hour is the pickup hour.");
    } catch (error) {
        box.textContent = "could not load hourly data.";
        console.error(error);

    }
}

async function loadEconomics() {
    const box = document.querySelector("#economics-chart");

    try {
        const rows = await getEconomics(readDayType());
        const hour = document.querySelector("#hour-filter").value;
        box.replaceChildren();
        box.classList.add("loaded");

        const toNumber = value => (value === null || value === undefined ? null : Number(value));
        drawBars(box, "Average fare ($)", HOUR_LABELS.map(h => toNumber(getValue(rows, "hour", "avg_fare", h))), hour, "$");
        drawBars(box, "Average fees ($)", HOUR_LABELS.map(h => toNumber(getValue(rows, "hour", "avg_fees", h))), hour, "$");
        drawBars(box, "Card tip rate (% of fare)", HOUR_LABELS.map(h => toNumber(getValue(rows, "hour", "card_tip_pct", h))), hour, "%");
    } catch (error) {
        box.textContent = "Could not load economics data.";
        console.error(error);
    }
}

async function loadHeatmap() {
    const grid = document.querySelector("#heatmap");
    const metric = document.querySelector("#heatmap-metric").value;
    const range = document.querySelector("#heatmap-range");
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    try {
        const rows = await getHeatmap(metric);
        grid.replaceChildren();

        const values = rows.map(row => row.value).filter(value => value !== null);
        const smallest = Math.min(...values);
        const largest = Math.max(...values);

        grid.appendChild(document.createElement("span"));
        HOUR_LABELS.forEach(hour => {
            const label = document.createElement("span");
            label.className = "heat-label";
            label.textContent = hour % 3 === 0 ? hour : "";
            grid.appendChild(label);
        });

        days.forEach((day, dow) => {
            const name = document.createElement("span");
            name.className = "heat-label";
            name.textContent = day;
            grid.appendChild(name);

            HOUR_LABELS.forEach(hour => {
                const cell = document.createElement("div");
                cell.className = "heat-cell";
                const row = rows.find(item => item.dow === dow && item.hour === hour);

                if (row && row.value !== null) {
                    const share = largest === smallest ? 0 : (row.value - smallest) / (largest - smallest);
                    cell.style.background = `rgba(3, 105, 161, ${0.1 + share * 0.9})`;
                    cell.title = `${day} ${hour}:00 - ${row.value.toFixed(1)} (${row.trips} trips)`;
                }
                grid.appendChild(cell);
            });
        });

        range.textContent = `Lightest cell: ${smallest.toFixed(1)}. Darkest cell: ${largest.toFixed(1)}. Hover a cell for its numbers.`;
    } catch (error) {
        grid.textContent = "Could not load the heatmap.";
        console.error(error);
    }
}

async function loadTrust() {
    const reasons = document.querySelector("#exclusion-reasons");
    const summaryText = document.querySelector("#quality-summary");

    try {
        const summary = await getTrustSummary();
        const byHour = await getRawVsClean("all");
        reasons.replaceChildren();

        let excluded = 0;
        let flagged = 0;
        summary.forEach(rule => {
            if (rule.action === "EXCLUDED") {
                excluded += Number(rule.row_count);
            } else {
                flagged += Number(rule.row_count);
            }

            if (Number(rule.row_count) === 0) {
                return;
            }
            const item = document.createElement("li");
            item.textContent = `${rule.reason_code} (${rule.action.toLowerCase()}): ${Number(rule.row_count).toLocaleString()} records, ${Number(rule.pct_of_raw).toFixed(2)}% - ${rule.description}`;
            reasons.appendChild(item);
        });

        const cleaned = combineDayTypes(byHour, "hour", ["mean_speed_mph"], "trips");
        const raw = combineDayTypes(byHour, "hour", ["raw_mean_speed_mph"], "raw_trips");
        const cleanedSpeed = averageOf(cleaned, "mean_speed_mph");
        const rawSpeed = averageOf(raw, "raw_mean_speed_mph");

        summaryText.textContent = `Rules removed ${excluded.toLocaleString()} records (one trip can break several rules) and flagged ${flagged.toLocaleString()} more that we kept. Mean speed is ${rawSpeed.toFixed(2)} mph before cleaning and ${cleanedSpeed.toFixed(2)} mph after.`;

        const total = byHour.reduce((sum, row) => sum + Number(row.trips), 0);
        const medians = combineDayTypes(await getHourProfile("all"), "hour", ["median_speed_mph"]);
        document.querySelector("#total-trips").textContent = total.toLocaleString();
        document.querySelector("#median-speed").textContent = averageOf(medians, "median_speed_mph").toFixed(1);
        document.querySelector("#excluded-trips").textContent = excluded.toLocaleString();
    } catch (error) {
        summaryText.textContent = "Could not load the data-quality information.";
        console.error(error);
    }
}

// average of a column over the rows, each row counted by its weight
function averageOf(rows, name) {
    let sum = 0;
    let weight = 0;

    rows.forEach(row => {
        if (row[name] !== null) {
            sum += row[name] * row.weight;
            weight += row.weight;
        }
    });

    return weight === 0 ? 0 : sum / weight;
}
