const fs = require("node:fs");
const assert = require("node:assert/strict");
const { JSDOM, VirtualConsole } = require("jsdom");
const errors = [];
const log = new VirtualConsole();
log.on("jsdomError", (error) => errors.push(error.message));
const html = fs.readFileSync(process.argv[2], "utf8");
const dom = new JSDOM(html, {
  runScripts: "dangerously",
  virtualConsole: log,
  beforeParse(window) {
    window.URL.createObjectURL = () => "blob:test-results";
    window.URL.revokeObjectURL = () => {};
    window.HTMLAnchorElement.prototype.click = function () {};
  },
});
const document = dom.window.document;
const metrics = () => document.querySelector("#metrics").textContent;
const expected = JSON.parse(document.querySelector("#results").textContent);
const initial = expected.sensitivity[String(expected.radius_m)];
assert(metrics().includes((initial.recall_at_1 * 100).toFixed(1) + "%"));
assert(
  document
    .querySelector("#baseline")
    .textContent.includes("at " + expected.radius_m + " m"),
);
assert(
  document
    .querySelector("#baseline")
    .textContent.includes(initial.hits_at_1 + "/" + initial.eligible_queries),
);
assert(
  metrics().includes(
    (initial.top1_within_radius_all_queries * 100).toFixed(1) + "%",
  ),
);
assert.equal(document.querySelectorAll(".candidate").length, 5);
assert.equal(document.querySelectorAll("[data-index]").length, 40);
document.querySelector("#filter").value = "miss";
document.querySelector("#filter").dispatchEvent(new dom.window.Event("change"));
assert.equal(
  document.querySelectorAll("[data-index]").length,
  40 - initial.hits_at_1,
);
document.querySelector("[data-index]").click();
assert(
  document.querySelector("#title").textContent.includes("false retrieval") ||
    document.querySelector("#title").textContent.includes("No positive"),
);
document.querySelector('[data-candidate="1"]').click();
assert(
  document.querySelector('[data-candidate="1"]').classList.contains("active"),
);
document.querySelector("#radius").value = "5";
document.querySelector("#radius").dispatchEvent(new dom.window.Event("change"));
assert(
  metrics().includes(expected.sensitivity["5"].eligible_queries + " / 40"),
);
assert(document.querySelector("#baseline").textContent.includes("at 5 m"));
document.querySelector("#filter").value = "uncovered";
document.querySelector("#filter").dispatchEvent(new dom.window.Event("change"));
assert.equal(
  document.querySelectorAll("[data-index]").length,
  40 - expected.sensitivity["5"].eligible_queries,
);
assert(document.querySelector("#queryimg").src.startsWith("data:image/jpeg"));
assert.equal(document.querySelectorAll("#route circle").length, 122);
document.querySelector("#download").click();
// Force an empty filter to exercise the empty-state branch.
dom.window.eval(
  "data.queries.forEach(q => q.nearest_reference_distance_m = 0)",
);
document.querySelector("#filter").dispatchEvent(new dom.window.Event("change"));
assert.equal(document.querySelectorAll("[data-index]").length, 0);
assert.equal(document.querySelector("#detailpanel").hidden, true);
document.querySelector("#filter").value = "all";
document.querySelector("#filter").dispatchEvent(new dom.window.Event("change"));
assert.equal(document.querySelector("#detailpanel").hidden, false);
assert.deepEqual(errors, []);
console.log(
  "PASS: HTML initialization, query selection, candidate selection, radius sensitivity, filtering, map generation and export handler",
);
dom.window.close();
