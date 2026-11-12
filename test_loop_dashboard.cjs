const fs = require('node:fs');
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');
const errors = [];
const log = new VirtualConsole();
log.on('jsdomError', error => errors.push(error.message));
const dom = new JSDOM(fs.readFileSync(process.argv[2], 'utf8'), {
  runScripts: 'dangerously', virtualConsole: log,
  beforeParse(w) {
    w.URL.createObjectURL = () => 'blob:test';
    w.URL.revokeObjectURL = () => {};
    w.HTMLAnchorElement.prototype.click = function() {};
  },
});
const d = dom.window.document;
const data = JSON.parse(d.querySelector('#study').textContent);
const change = (id, value) => {
  d.querySelector('#' + id).value = value;
  d.querySelector('#' + id).dispatchEvent(new dom.window.Event('change'));
};
assert.equal(d.querySelectorAll('[data-query]').length, 40);
assert.equal(d.querySelectorAll('[data-candidate]').length, 3);
assert(d.querySelector('#metrics').textContent.includes('21/33'));
assert(d.querySelector('#metrics').textContent.includes('11/11'));
assert(d.querySelector('#queryimage').src.startsWith('data:image/jpeg'));
assert(d.querySelectorAll('#alignment circle').length > 0);
d.querySelector('[data-candidate="1"]').click();
assert(d.querySelector('[data-candidate="1"]').classList.contains('active'));
change('filter', 'accepted');
assert.equal(d.querySelectorAll('[data-query]').length, 11);
change('filter', 'abstain');
assert.equal(d.querySelectorAll('[data-query]').length, 29);
change('filter', 'false');
assert.equal(d.querySelectorAll('[data-query]').length, 0);
assert.equal(d.querySelector('#detail').hidden, true);
change('radius', '10');
assert.equal(d.querySelectorAll('[data-query]').length, 1);
assert.equal(d.querySelector('#detail').hidden, false);
assert(d.querySelector('#metrics').textContent.includes('90.9%'));
assert(d.querySelector('#metrics').textContent.includes('10/11'));
assert(d.querySelector('#pairinfo').textContent.includes('outside'));
change('filter', 'all');
d.querySelector('[data-query="2"]').click();
assert(d.querySelector('#heading').textContent.includes(data.queries[2].id));
change('radius', '5');
assert(d.querySelector('#metrics').textContent.includes('11/11 eligible queries'));
d.querySelector('#export').click();
assert.deepEqual(errors, []);
console.log('PASS: learned dashboard metrics, candidate/query selection, geometry, abstentions, empty filter, radius sensitivity, export');
dom.window.close();
