const API_BASE_URL = "http://127.0.0.1:5000";

async function getJSON(path) {
    const response = await fetch(`${API_BASE_URL}${path}`);

    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }

    return response.json();

}

function checkApiHealth() {
    return getJSON("/api/health");
}

function getZones() {
    return getJSON("/api/zones");
}

function getSlowestZones() {
    return getJSON("/api/zones/slowest?k=10&min_trips=30");
}

function getSpeedByHour(weekend = ""){
    const query = weekend === "" ? "" : `?weekend=${weekend}`;
    return getJSON(`/api/insights/speed-by-hour${query}`);
}

function getCostofSlowness(weekend = "") {
    const query = weekend === "" ? "" : `?weekend=${weekend}`;
    return getJSON(`/api/insights/cost-of-slowness${query}`);
}



