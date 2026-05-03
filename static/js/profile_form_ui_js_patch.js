/**
 * profile_form_ui_js_patch.js
 * ============================
 * JavaScript additions for the new profile form fields.
 *
 * HOW TO USE:
 *   Copy-paste each function into dashboard.html's <script> block,
 *   next to the existing ep* functions.
 *   Then wire them into epSaveProfile() and epPopulateForm() as shown
 *   at the bottom of this file.
 */

// ─── Conditional visibility helpers ──────────────────────────────────────────

/** Show/hide the occupation-type row based on employment status */
function epToggleOccupationType() {
  const status = document.getElementById('ep-employment_status')?.value || '';
  const show   = status === 'Employed (Salaried)' || status === 'Self-Employed';
  document.getElementById('ep-occupation-type-row').style.display = show ? '' : 'none';
}

/** Show/hide years-in-state once a state is chosen */
function epToggleYearsInState() {
  const state = document.getElementById('ep-state')?.value || '';
  document.getElementById('ep-years-in-state-row').style.display = state ? '' : 'none';
}

/** Show/hide pregnancy & lactating rows for female users */
function epToggleHealthRows() {
  const gender = epGetTg('ep-gender-group') || '';
  const isFemale = gender.toLowerCase() === 'female';
  document.getElementById('ep-pregnant-row').style.display  = isFemale ? '' : 'none';
  document.getElementById('ep-lactating-row').style.display = isFemale ? '' : 'none';
}

/** Show/hide disability details list */
function epToggleDisabilityDetails() {
  const isDisabled = epGetTg('ep-disability-group') === 'Yes';
  document.getElementById('ep-disability-details-row').style.display = isDisabled ? '' : 'none';
}

/** Show/hide irrigated toggle for agricultural land rows */
function epToggleLandIrrigated(selectEl) {
  const row = selectEl.closest('.ep-land-row');
  const irrigatedRow = row.querySelector('.ep-lp-irrigated-row');
  irrigatedRow.style.display = selectEl.value === 'Agricultural' ? '' : 'none';
}

/** Sync social_category → legacy caste field so existing engine still works */
function epSyncCasteLegacy() {
  const cat = document.getElementById('ep-social_category')?.value || '';
  const legacyCasteMap = {
    'Scheduled Caste (SC)':                           'SC',
    'Scheduled Tribe (ST)':                           'ST',
    'Other Backward Class (OBC) - Non-Creamy Layer':  'OBC',
    'Other Backward Class (OBC) - Creamy Layer':      'OBC',
    'Economically Weaker Section (EWS)':              'General',
    'General':                                        'General',
    'Minority':                                       'General',
    'Denotified/Nomadic/Semi-Nomadic Tribes (DNT/NT/SNT)': 'ST',
  };
  const legacyCaste = document.getElementById('ep-caste');
  if (legacyCaste) legacyCaste.value = legacyCasteMap[cat] || '';
  epTrackProgress();
}

// ─── Generic toggle helper for rows (used inside cloned templates) ───────────

function epTgInRow(btn, groupClass, val) {
  const row = btn.closest('[class$="-row"]');
  row.querySelectorAll('.' + groupClass + ' .ep-btn').forEach(b => b.classList.remove('ep-active'));
  btn.classList.add('ep-active');
  epTrackProgress();
}

// ─── Family Members ───────────────────────────────────────────────────────────

function epAddFamilyMember() {
  const tpl  = document.getElementById('ep-family-member-tpl');
  const list = document.getElementById('ep-family-list');
  list.appendChild(tpl.content.cloneNode(true));
}

function epRemoveFamilyMember(btn) {
  btn.closest('.ep-family-row').remove();
  epTrackProgress();
}

function epSerializeFamilyMembers() {
  return Array.from(document.querySelectorAll('#ep-family-list .ep-family-row')).map(row => ({
    relation:      row.querySelector('.ep-fm-relation')?.value   || '',
    date_of_birth: row.querySelector('.ep-fm-dob')?.value        || '',
    is_alive:      (row.querySelector('.ep-fm-alive-group .ep-btn.ep-active')?.dataset.val || 'Yes') === 'Yes',
  }));
}

function epPopulateFamilyMembers(members) {
  const list = document.getElementById('ep-family-list');
  list.innerHTML = '';
  (members || []).forEach(m => {
    epAddFamilyMember();
    const row = list.lastElementChild;
    row.querySelector('.ep-fm-relation').value = m.relation      || '';
    row.querySelector('.ep-fm-dob').value       = m.date_of_birth || '';
    const aliveVal = m.is_alive === false ? 'No' : 'Yes';
    row.querySelectorAll('.ep-fm-alive-group .ep-btn').forEach(b => {
      b.classList.toggle('ep-active', b.dataset.val === aliveVal);
    });
  });
}

// ─── Land Ownership ───────────────────────────────────────────────────────────

function epAddLandParcel() {
  const tpl  = document.getElementById('ep-land-parcel-tpl');
  const list = document.getElementById('ep-land-list');
  list.appendChild(tpl.content.cloneNode(true));
}

function epRemoveLandParcel(btn) {
  btn.closest('.ep-land-row').remove();
  epTrackProgress();
}

function epSerializeLandParcels() {
  return Array.from(document.querySelectorAll('#ep-land-list .ep-land-row')).map(row => ({
    area_in_acres: parseFloat(row.querySelector('.ep-lp-acres')?.value) || 0,
    land_type:     row.querySelector('.ep-lp-type')?.value || '',
    is_irrigated:  (row.querySelector('.ep-lp-irrigated-group .ep-btn.ep-active')?.dataset.val || 'No') === 'Yes',
  }));
}

function epPopulateLandParcels(parcels) {
  const list = document.getElementById('ep-land-list');
  list.innerHTML = '';
  (parcels || []).forEach(p => {
    epAddLandParcel();
    const row  = list.lastElementChild;
    const typeEl = row.querySelector('.ep-lp-type');
    row.querySelector('.ep-lp-acres').value = p.area_in_acres || '';
    typeEl.value = p.land_type || '';
    epToggleLandIrrigated(typeEl);
    const irrigatedVal = p.is_irrigated ? 'Yes' : 'No';
    row.querySelectorAll('.ep-lp-irrigated-group .ep-btn').forEach(b => {
      b.classList.toggle('ep-active', b.dataset.val === irrigatedVal);
    });
  });
}

// ─── Education Details ────────────────────────────────────────────────────────

function epAddEduEntry() {
  const tpl  = document.getElementById('ep-edu-entry-tpl');
  const list = document.getElementById('ep-edu-list');
  list.appendChild(tpl.content.cloneNode(true));
}

function epRemoveEduEntry(btn) {
  btn.closest('.ep-edu-row').remove();
  epTrackProgress();
}

function epSerializeEduEntries() {
  return Array.from(document.querySelectorAll('#ep-edu-list .ep-edu-row')).map(row => ({
    education_level:   row.querySelector('.ep-edu-level')?.value  || '',
    stream:            row.querySelector('.ep-edu-stream')?.value || '',
    status:            row.querySelector('.ep-edu-status')?.value || '',
    percentage_marks:  parseFloat(row.querySelector('.ep-edu-pct')?.value)  || null,
    year_of_passing:   parseInt(row.querySelector('.ep-edu-year')?.value)   || null,
    institute_type:    row.querySelector('.ep-edu-inst')?.value   || '',
  }));
}

function epPopulateEduEntries(entries) {
  const list = document.getElementById('ep-edu-list');
  list.innerHTML = '';
  (entries || []).forEach(e => {
    epAddEduEntry();
    const row = list.lastElementChild;
    row.querySelector('.ep-edu-level').value  = e.education_level  || '';
    row.querySelector('.ep-edu-stream').value = e.stream           || '';
    row.querySelector('.ep-edu-status').value = e.status           || '';
    row.querySelector('.ep-edu-pct').value    = e.percentage_marks != null ? e.percentage_marks : '';
    row.querySelector('.ep-edu-year').value   = e.year_of_passing  || '';
    row.querySelector('.ep-edu-inst').value   = e.institute_type   || '';
  });
}

// ─── Disability Details ───────────────────────────────────────────────────────

function epAddDisabilityEntry() {
  const tpl  = document.getElementById('ep-disability-entry-tpl');
  const list = document.getElementById('ep-disability-list');
  list.appendChild(tpl.content.cloneNode(true));
}

function epRemoveDisabilityEntry(btn) {
  btn.closest('.ep-dis-row').remove();
  epTrackProgress();
}

function epSerializeDisabilityEntries() {
  return Array.from(document.querySelectorAll('#ep-disability-list .ep-dis-row')).map(row => ({
    disability_type:       row.querySelector('.ep-dis-type')?.value    || '',
    disability_percentage: parseInt(row.querySelector('.ep-dis-pct')?.value) || null,
  }));
}

function epPopulateDisabilityEntries(entries) {
  const list = document.getElementById('ep-disability-list');
  list.innerHTML = '';
  (entries || []).forEach(e => {
    epAddDisabilityEntry();
    const row = list.lastElementChild;
    row.querySelector('.ep-dis-type').value = e.disability_type || '';
    row.querySelector('.ep-dis-pct').value  = e.disability_percentage != null ? e.disability_percentage : '';
  });
}

// ─── epSaveProfile additions ─────────────────────────────────────────────────
// In the existing epSaveProfile() function, add these fields to the payload
// object before the fetch call.  Paste into the existing payload = { ... }:
/*
    // ── NEW FIELDS ────────────────────────────────────────────────────────
    socialCategory:              document.getElementById('ep-social_category')?.value || '',
    dateOfBirth:                 document.getElementById('ep-dob')?.value || '',
    annualFamilyIncome:          parseInt(document.getElementById('ep-annual_family_income')?.value) || 0,
    isBpl:                       epGetTg('ep-bpl-group'),
    hasBankAccount:              epGetTg('ep-bank-account-v2-group'),
    employmentStatus:            document.getElementById('ep-employment_status')?.value || '',
    occupationTypeNew:           document.getElementById('ep-occupation_type')?.value  || '',
    disabilityDetails:           epSerializeDisabilityEntries(),
    familyMembers:               epSerializeFamilyMembers(),
    landOwnershipDetails:        epSerializeLandParcels(),
    educationDetails:            epSerializeEduEntries(),
    stateOfDomicile:             document.getElementById('ep-state')?.value || '',
    residenceLocationType:       epGetTg('ep-residence-group'),
    yearsInCurrentState:         parseInt(document.getElementById('ep-years_in_current_state')?.value) || null,
    isExServicemanOrDependent:   epGetTg('ep-ex-serviceman-group'),
    isShgMember:                 epGetTg('ep-shg-group'),
    isFreedomFighterOrDependent: epGetTg('ep-freedom-fighter-group'),
    hasCriticalIllness:          epGetTg('ep-critical-illness-group'),
    isPregnant:                  epGetTg('ep-pregnant-group'),
    isLactatingMother:           epGetTg('ep-lactating-group'),
    // ── END NEW FIELDS ────────────────────────────────────────────────────
*/

// ─── epPopulateForm additions ─────────────────────────────────────────────────
// In the existing epPopulateForm(p) function, add these lines.
// 'p' is the profile object returned by the server.
/*
    // ── NEW FIELDS ────────────────────────────────────────────────────────
    if (document.getElementById('ep-social_category'))
        document.getElementById('ep-social_category').value = p.socialCategory || '';
    epTg('ep-bpl-group',               p.isBpl             || '');
    epTg('ep-bank-account-v2-group',   p.hasBankAccount    || '');
    epTg('ep-ex-serviceman-group',     p.isExServicemanOrDependent  || '');
    epTg('ep-shg-group',               p.isShgMember       || '');
    epTg('ep-freedom-fighter-group',   p.isFreedomFighterOrDependent || '');
    epTg('ep-critical-illness-group',  p.hasCriticalIllness || '');
    epTg('ep-pregnant-group',          p.isPregnant        || '');
    epTg('ep-lactating-group',         p.isLactatingMother || '');
    if (document.getElementById('ep-occupation_type'))
        document.getElementById('ep-occupation_type').value = p.occupationTypeNew || '';
    if (document.getElementById('ep-years_in_current_state'))
        document.getElementById('ep-years_in_current_state').value = p.yearsInCurrentState || '';

    // Structured lists
    try { epPopulateFamilyMembers(typeof p.familyMembers === 'string'
            ? JSON.parse(p.familyMembers) : p.familyMembers); } catch(e){}
    try { epPopulateLandParcels(typeof p.landOwnershipDetails === 'string'
            ? JSON.parse(p.landOwnershipDetails) : p.landOwnershipDetails); } catch(e){}
    try { epPopulateEduEntries(typeof p.educationDetails === 'string'
            ? JSON.parse(p.educationDetails) : p.educationDetails); } catch(e){}
    try { epPopulateDisabilityEntries(typeof p.disabilityDetails === 'string'
            ? JSON.parse(p.disabilityDetails) : p.disabilityDetails); } catch(e){}

    // Trigger visibility toggles
    epToggleOccupationType();
    epToggleYearsInState();
    epToggleHealthRows();
    epToggleDisabilityDetails();
    // ── END NEW FIELDS ────────────────────────────────────────────────────
*/

// ─── to_dict() additions (server side) ───────────────────────────────────────
// In User.to_dict(), add these keys to the returned dict:
/*
    'socialCategory':             self.social_category,
    'dateOfBirth':                self.date_of_birth_v2,
    'annualFamilyIncome':         self.annual_family_income_v2 or self.annual_family_income,
    'isBpl':                      self.is_bpl_v2,
    'hasBankAccount':             self.has_bank_account_v2,
    'employmentStatus':           self.employment_status_v2 or self.employment_status,
    'occupationTypeNew':          self.occupation_type,
    'disabilityDetails':          json.loads(self.disability_details) if self.disability_details else [],
    'familyMembers':              json.loads(self.family_members)      if self.family_members      else [],
    'landOwnershipDetails':       json.loads(self.land_ownership_details) if self.land_ownership_details else [],
    'educationDetails':           json.loads(self.education_details)   if self.education_details   else [],
    'stateOfDomicile':            self.state_of_domicile,
    'residenceLocationType':      self.residence_location_type,
    'yearsInCurrentState':        self.years_in_current_state,
    'isExServicemanOrDependent':  self.is_ex_serviceman_or_dependent,
    'isShgMember':                self.is_shg_member,
    'isFreedomFighterOrDependent':self.is_freedom_fighter_or_dependent,
    'hasCriticalIllness':         self.has_critical_illness,
    'isPregnant':                 self.is_pregnant,
    'isLactatingMother':          self.is_lactating_mother,
*/

// ─── Event listener wiring ────────────────────────────────────────────────────
// ADD these inside the DOMContentLoaded block (or wherever existing listeners
// are attached):
/*
    // New conditional visibility wires
    document.getElementById('ep-employment_status')
        ?.addEventListener('change', epToggleOccupationType);
    document.getElementById('ep-state')
        ?.addEventListener('change', epToggleYearsInState);
    document.querySelectorAll('#ep-gender-group .ep-btn')
        .forEach(b => b.addEventListener('click', epToggleHealthRows));
    document.querySelectorAll('#ep-disability-group .ep-btn')
        .forEach(b => b.addEventListener('click', epToggleDisabilityDetails));
*/
