// ========== SUPABASE CONFIG ==========
// REPLACE WITH YOUR ACTUAL SUPABASE CREDENTIALS
const SUPABASE_URL = "https://wqlbmtjbjloxpvsbeqyb.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_gcyK2z_8lvbOgHNcJfdX1g_8QCWJ_Xi";
const GOOGLE_SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSYgD018ww2Mbkud6ZYmZHop7EXxcm_0Zl4V9bB2AaY4r4xXTWChAW6v-gUyjD4-2Qmg4H8O0kxryCf/pub?output=csv";

let _supabase = null;
let patients = [];
let currentEditId = null;
let pendingConfirmCallback = null;
let currentTab = 'all';
let searchQuery = '';
let pendingInjectionId = null;
let pendingAppointmentId = null;

const doseToWeeks = { '7.5': 4, '22.5': 12, '30': 16, '45': 24 };

const columnMapping = {
    'Patient Name': 'patient_name',
    'File Number': 'file_number',
    'Address': 'address',
    'Phone 1': 'phone1',
    'Phone 2': 'phone2',
    'Dose Prescribed': 'dose_prescribed',
    'Total Doses': 'total_doses',
    'Doses Remaining': 'doses_remaining',
    'Previous Injection Site': 'previous_injection_site',
    'Injection Site': 'injection_site',
    'Due Date': 'due_date',
    'Appointment Date & Time': 'appointment_date_time',
    'Previous Injection Dates': 'previous_injection_dates',
    'Assignment Type': 'assignment_type',
    'Special Instructions': 'special_instructions',
    'Adverse Effects Comments': 'adverse_effects_comments',
    'File Status': 'file_status',
    'Injection Administered': 'injection_administered',
    'Appointment Confirmed': 'appointment_confirmed',
    'Pending': 'pending',
    'Archived': 'archived'
};

// ========== DATE FUNCTIONS (NO TIMEZONE SHIFT) ==========
function getTodayLocal() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function addWeeksToDateStr(dateStr, weeks) {
    if (!dateStr) return getTodayLocal();
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    date.setDate(date.getDate() + (weeks * 7));
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function formatDisplayDate(dateStr) {
    if (!dateStr) return 'Not set';
    const d = new Date(dateStr);
    return d.toLocaleDateString();
}

// ========== SUPABASE ==========
async function initSupabase() {
    if (SUPABASE_URL === "https://YOUR_PROJECT_ID.supabase.co") {
        document.getElementById('syncStatus').innerHTML = '⚠️ Configure Supabase';
        return false;
    }
    try {
        _supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        await _supabase.from('patients').select('count', { count: 'exact', head: true });
        document.getElementById('syncStatus').innerHTML = '✅ Connected';
        return true;
    } catch (e) {
        console.error(e);
        document.getElementById('syncStatus').innerHTML = '❌ Failed';
        return false;
    }
}

async function loadPatients() {
    if (!_supabase) return;
    document.getElementById('loadingOverlay').style.display = 'flex';
    try {
        const { data, error } = await _supabase.from('patients').select('*').order('created_at', { ascending: false });
        if (error) throw error;
        patients = data.map(row => {
            const p = {};
            for (let [k, v] of Object.entries(columnMapping)) p[k] = row[v];
            p.id = row.id;
            return p;
        });
        document.getElementById('recordCount').innerHTML = `📋 ${patients.length}`;
        renderCurrentTab();
    } catch (e) {
        console.error(e);
        alert('Load error: ' + e.message);
    } finally {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}

async function addPatientToDB(p) {
    const db = {};
    for (let [k, v] of Object.entries(columnMapping)) db[v] = p[k] || null;
    const { error } = await _supabase.from('patients').insert([db]);
    if (error) {
        alert('Error: ' + error.message);
        return false;
    }
    return true;
}

async function updatePatientInDB(id, p) {
    const db = {};
    for (let [k, v] of Object.entries(columnMapping)) db[v] = p[k] || null;
    const { error } = await _supabase.from('patients').update(db).eq('id', id);
    if (error) {
        alert('Error: ' + error.message);
        return false;
    }
    return true;
}

async function deletePatientFromDB(id) {
    const { error } = await _supabase.from('patients').delete().eq('id', id);
    if (error) {
        alert('Error: ' + error.message);
        return false;
    }
    return true;
}

// ========== PDF EXTRACTION ==========
async function importPDF(file) {
    const f = document.getElementById('pdfFileInput').files[0];
    if (!f || f.type !== 'application/pdf') {
        alert('Select a PDF');
        return;
    }
    document.getElementById('loadingOverlay').style.display = 'flex';
    try {
        const buf = await f.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: buf }).promise;
        let fullText = '';
        for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const tc = await page.getTextContent();
            fullText += tc.items.map(t => t.str).join(' ') + '\n';
        }
        document.getElementById('loadingOverlay').style.display = 'none';

        let name = null, fileNo = null, dose = null, addr = null, phone1 = null, phone2 = null, injDate = null;
        
        const nMatch = fullText.match(/PATIENT NAME\/NOM DU PATIENT\s*([A-Z][A-Z\s]+[A-Z])/i);
        if (nMatch) name = nMatch[1].trim().replace(/\s+/g, ' ');
        
        const fMatch = fullText.match(/MEDICUM\s*#:\s*(\d+)/i);
        if (fMatch) fileNo = fMatch[1];
        
        const dMatch = fullText.match(/(\d+\.?\d*)\s*mg/i);
        if (dMatch && [7.5, 22.5, 30, 45].includes(parseFloat(dMatch[1]))) dose = parseFloat(dMatch[1]).toString();
        
        let addrParts = [];
        const street = fullText.match(/ADDRESS\/ADRESSE\s*([A-Za-z0-9\s,.'-]+)/i);
        if (street) addrParts.push(street[1].trim());
        const city = fullText.match(/CITY\/VILLE\s*([A-Za-zÀ-ÿ\s.'-]+(?:,?\s*[A-Z]{2})?)/i);
        if (city) addrParts.push(city[1].trim());
        const postal = fullText.match(/\b([A-Z]\d[A-Z]\s?\d[A-Z]\d)\b/i);
        if (postal && !addrParts.some(p => p.includes(postal[1]))) addrParts.push(postal[1].trim());
        if (addrParts.length) addr = addrParts.join(', ').replace(/\s+/g, ' ').trim();
        
        const p1 = fullText.match(/TELEPHONE\/TELEPHONE\s*(\d{3}\s?\d{3}\s?\d{4})/i);
        if (p1) phone1 = p1[1].replace(/\s/g, '');
        else {
            const pStd = fullText.match(/TELEPHONE\s*(\d{3}\s?\d{3}\s?\d{4})/i);
            if (pStd) phone1 = pStd[1].replace(/\s/g, '');
        }
        
        const pSec = fullText.match(/SECONDARY CONTACT[^0-9]*(\d{3}\s?\d{3}\s?\d{4})/i);
        if (pSec) phone2 = pSec[1].replace(/\s/g, '');
        
        const iMatch = fullText.match(/injection seulement\s+(\d{1,2})\s+([A-Za-zéè]+)\s+(\d{4})/i);
        if (iMatch) {
            const months = { janvier: '01', février: '02', mars: '03', avril: '04', mai: '05', juin: '06', juillet: '07', août: '08', septembre: '09', octobre: '10', novembre: '11', décembre: '12' };
            injDate = `${iMatch[3]}-${months[iMatch[2].toLowerCase()]}-${iMatch[1].padStart(2, '0')}`;
        }
        
        if (name && fileNo && confirm(`Add: ${name} (${fileNo})?`)) {
            await addPatient({
                'Patient Name': name,
                'File Number': fileNo,
                'Address': addr || '',
                'Phone 1': phone1 || '',
                'Phone 2': phone2 || '',
                'Dose Prescribed': dose || '7.5',
                'Total Doses': '4',
                'Doses Remaining': '4',
                'Previous Injection Site': '',
                'Injection Site': '',
                'Due Date': getTodayLocal(),
                'Appointment Date & Time': injDate || null,
                'Previous Injection Dates': '',
                'Assignment Type': 'Permanent',
                'Special Instructions': '',
                'Adverse Effects Comments': '',
                'File Status': 'Active',
                'Injection Administered': false,
                'Appointment Confirmed': !!injDate,
                'Pending': false,
                'Archived': false
            });
            alert('Patient added');
        } else {
            alert('Could not extract required data');
        }
    } catch (e) {
        alert('PDF error: ' + e.message);
    } finally {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}

// ========== GOOGLE SHEETS IMPORT ==========
async function importFromGoogleSheets() {
    if (!confirm('Import from Google Sheets?')) return;
    document.getElementById('loadingOverlay').style.display = 'flex';
    try {
        const resp = await fetch(GOOGLE_SHEETS_CSV_URL);
        const csv = await resp.text();
        const rows = csv.split('\n');
        const headers = rows[0].split(',').map(h => h.trim().replace(/"/g, ''));
        let imported = 0, dup = 0;
        for (let i = 1; i < rows.length; i++) {
            if (!rows[i].trim()) continue;
            let vals = [], inQ = false, cur = '';
            for (let ch of rows[i]) {
                if (ch === '"') inQ = !inQ;
                else if (ch === ',' && !inQ) {
                    vals.push(cur.trim().replace(/^"|"$/g, ''));
                    cur = '';
                } else cur += ch;
            }
            vals.push(cur.trim().replace(/^"|"$/g, ''));
            const p = {};
            headers.forEach((h, idx) => p[h] = vals[idx] || '');
            if (p['Patient Name'] && !patients.find(ex => ex['File Number'] === p['File Number'])) {
                await addPatient({
                    'Patient Name': p['Patient Name'],
                    'File Number': p['File Number'],
                    'Address': p['Address'] || '',
                    'Phone 1': p['Phone 1'] || '',
                    'Phone 2': p['Phone 2'] || '',
                    'Dose Prescribed': p['Dose Prescribed'] || '7.5',
                    'Total Doses': p['Total Doses'] || '4',
                    'Doses Remaining': p['Doses Remaining'] || '4',
                    'Previous Injection Site': '',
                    'Injection Site': '',
                    'Due Date': getTodayLocal(),
                    'Appointment Date & Time': null,
                    'Previous Injection Dates': '',
                    'Assignment Type': 'Permanent',
                    'Special Instructions': '',
                    'Adverse Effects Comments': '',
                    'File Status': 'Active',
                    'Injection Administered': false,
                    'Appointment Confirmed': false,
                    'Pending': false,
                    'Archived': false
                });
                imported++;
            } else dup++;
        }
        alert(`Imported ${imported}, skipped ${dup}`);
        await loadPatients();
    } catch (e) {
        alert('Import error: ' + e.message);
    } finally {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}

// ========== DOSING LOGIC ==========
function getReferenceDateForDueDate(p) {
    const today = getTodayLocal();
    const apptOnly = p['Appointment Date & Time'] ? p['Appointment Date & Time'].split('T')[0] : null;
    if (p['Appointment Confirmed'] && !p['Injection Administered'] && apptOnly && apptOnly < today) return apptOnly;
    return today;
}

function calculateNextDueDate(_, dose, ref) {
    return addWeeksToDateStr(ref, doseToWeeks[dose] || 4);
}

// ========== INJECTION FLOW ==========
function showInjectionModal(id) {
    pendingInjectionId = id;
    const p = patients.find(p => p.id === id);
    if (!p) return;
    document.getElementById('injectionPatientName').innerHTML = `<strong>${escapeHtml(p['Patient Name'])}</strong> (${p['Dose Prescribed']}mg, ${p['Doses Remaining']} left)`;
    document.getElementById('injectionCurrentInfo').innerHTML = `Next due: +${doseToWeeks[p['Dose Prescribed']]} weeks`;
    document.getElementById('injectionSiteSelect').value = '';
    document.getElementById('injectionSpecialInstructions').value = '';
    document.getElementById('injectionAdverseEvents').value = '';
    document.getElementById('injectionComments').value = '';
    document.getElementById('injectionModal').style.display = 'block';
}

async function performInjection() {
    const site = document.getElementById('injectionSiteSelect').value;
    if (!site) {
        alert('Select injection site');
        return;
    }
    const spec = document.getElementById('injectionSpecialInstructions').value;
    const adverse = document.getElementById('injectionAdverseEvents').value;
    const comments = document.getElementById('injectionComments').value;
    const id = pendingInjectionId;
    const p = patients.find(p => p.id === id);
    let left = parseInt(p['Doses Remaining']) || 0;
    const total = parseInt(p['Total Doses']) || 4;
    if (left <= 0) {
        alert('No doses left');
        closeInjModal();
        return;
    }
    const today = getTodayLocal();
    let prev = p['Previous Injection Dates'] ? p['Previous Injection Dates'].split(',') : [];
    prev.push(today);
    p['Previous Injection Dates'] = prev.join(', ');
    if (p['Injection Site']) p['Previous Injection Site'] = p['Injection Site'];
    p['Injection Site'] = site;
    if (spec) p['Special Instructions'] = (p['Special Instructions'] ? p['Special Instructions'] + ' | ' : '') + `[${today}] ${spec}`;
    if (adverse) p['Adverse Effects Comments'] = (p['Adverse Effects Comments'] ? p['Adverse Effects Comments'] + ' | ' : '') + `[${today}] ${adverse}`;
    if (comments) p['Special Instructions'] = (p['Special Instructions'] ? p['Special Instructions'] + ' | ' : '') + `[${today}] 💬 ${comments}`;
    const newLeft = left - 1;
    p['Doses Remaining'] = newLeft;
    const ref = getReferenceDateForDueDate(p);
    p['Due Date'] = calculateNextDueDate(p['Due Date'], p['Dose Prescribed'], ref);
    p['Injection Administered'] = true;
    p['Appointment Confirmed'] = false;
    p['Appointment Date & Time'] = null;
    p['Pending'] = (newLeft === 0);
    await updatePatientInDB(id, p);
    await loadPatients();
    closeInjModal();
    alert(`Injection recorded. ${newLeft} doses left. Next due: ${p['Due Date']}`);
}

function closeInjModal() {
    document.getElementById('injectionModal').style.display = 'none';
    pendingInjectionId = null;
}

// ========== APPOINTMENT CONFIRMATION ==========
function openAppointmentEditor(id) {
    pendingAppointmentId = id;
    const p = patients.find(p => p.id === id);
    document.getElementById('appointmentDateInput').value = p && p['Appointment Date & Time'] ? p['Appointment Date & Time'] : '';
    document.getElementById('apptEditModal').style.display = 'block';
}

async function saveAppointmentDate() {
    const id = pendingAppointmentId;
    const dt = document.getElementById('appointmentDateInput').value;
    if (!dt) {
        alert('Select date/time');
        return;
    }
    const p = patients.find(p => p.id === id);
    if (p) {
        p['Appointment Date & Time'] = dt;
        p['Appointment Confirmed'] = true;
        await updatePatientInDB(id, p);
        await loadPatients();
        alert(`Appointment confirmed for ${p['Patient Name']}`);
    }
    document.getElementById('apptEditModal').style.display = 'none';
    pendingAppointmentId = null;
}

// ========== CRUD ==========
async function addPatient(p) {
    const exists = patients.find(ex => ex['File Number'] === p['File Number']);
    if (exists) {
        alert('File number exists');
        return false;
    }
    const ok = await addPatientToDB(p);
    if (ok) await loadPatients();
    return ok;
}

async function updatePatient(p) {
    const ok = await updatePatientInDB(p.id, p);
    if (ok) await loadPatients();
    return ok;
}

async function deletePatient(id) {
    await deletePatientFromDB(id);
    await loadPatients();
}

async function markPending(id) {
    const p = patients.find(p => p.id === id);
    if (p) {
        p['Pending'] = true;
        await updatePatientInDB(id, p);
        await loadPatients();
    }
}

async function moveToAllPatients(id) {
    const p = patients.find(p => p.id === id);
    if (p) {
        p['Pending'] = false;
        p['Archived'] = false;
        await updatePatientInDB(id, p);
        await loadPatients();
    }
}

// ========== FILTER & RENDER ==========
function getFilteredPatients() {
    const today = getTodayLocal();
    return patients.filter(p => {
        if (p['Archived'] && currentTab !== 'archived') return false;
        if (!p['Archived'] && currentTab === 'archived') return false;
        if (p['Pending'] && currentTab !== 'pending') return false;
        if (!p['Pending'] && currentTab === 'pending') return false;
        if (currentTab === 'all') return !p['Archived'] && !p['Pending'] && !p['Appointment Confirmed'];
        const apptOnly = p['Appointment Date & Time'] ? p['Appointment Date & Time'].split('T')[0] : null;
        const confirmed = p['Appointment Confirmed'] === true;
        const isToday = apptOnly === today;
        const isFuture = apptOnly && apptOnly > today;
        const overdue = apptOnly && apptOnly < today && !p['Injection Administered'] && confirmed;
        if (currentTab === 'today') return isToday && confirmed && !overdue;
        if (currentTab === 'scheduled') return isFuture && confirmed;
        if (currentTab === 'overdue') return overdue;
        return false;
    }).filter(p => !searchQuery || p['Patient Name'].toLowerCase().includes(searchQuery) || p['File Number'].toLowerCase().includes(searchQuery))
        .sort((a, b) => (a['Due Date'] || '').localeCompare(b['Due Date'] || ''));
}

function renderPatientCard(p) {
    const dueDisplay = formatDisplayDate(p['Due Date']);
    const dose = p['Dose Prescribed'] || '';
    const total = parseInt(p['Total Doses']) || 4;
    const left = parseInt(p['Doses Remaining']) || 0;
    const given = total - left;
    const hasAppt = p['Appointment Date & Time'];
    const confirmed = p['Appointment Confirmed'];
    const apptDisplay = hasAppt ? new Date(p['Appointment Date & Time']).toLocaleString() : 'Not set';
    const special = p['Special Instructions'] || '';
    const progressPercent = (given / total) * 100;

    return `
        <div class="patient-card" data-id="${p.id}">
            <div class="patient-card__header">
                <div>
                    <span class="patient-name">${escapeHtml(p['Patient Name'])}</span>
                    <span class="patient-file">#${escapeHtml(p['File Number'])}</span>
                    ${dose ? `<span class="badge badge--dose">${dose}mg</span>` : ''}
                </div>
                <div class="patient-actions">
                    ${p['Phone 1'] ? `<button class="action-icon action-icon--call" data-phone="${escapeHtml(p['Phone 1'])}">📞</button>` : ''}
                    ${p['Phone 2'] ? `<button class="action-icon action-icon--call" data-phone="${escapeHtml(p['Phone 2'])}">📞2</button>` : ''}
                    ${p['Address'] ? `<button class="action-icon action-icon--map" data-address="${escapeHtml(p['Address'])}">📍</button>` : ''}
                </div>
            </div>
            <div class="patient-address">${escapeHtml(p['Address'] || 'No address')}</div>
            <div class="patient-due">📅 Due: ${dueDisplay}</div>
            <div class="progress">
                <div class="progress__bar"><div class="progress__fill" style="width: ${progressPercent}%"></div></div>
                <div class="progress__text">${given}/${total} doses</div>
            </div>
            ${special ? `<div class="badge badge--special">⚠️ ${escapeHtml(special.substring(0, 50))}${special.length > 50 ? '...' : ''}</div>` : ''}
            <div class="expanded-view">
                <div class="detail-row"><div class="detail-label">File:</div><div>${escapeHtml(p['File Number'])}</div></div>
                <div class="detail-row"><div class="detail-label">Dose:</div><div>${dose}mg (${doseToWeeks[dose] || 4} weeks)</div></div>
                <div class="detail-row"><div class="detail-label">Last Injection:</div><div>${escapeHtml(p['Injection Site'] || 'None')}</div></div>
                <div class="detail-row"><div class="detail-label">Appointment:</div><div>${apptDisplay}<span class="edit-icon" onclick="openAppointmentEditor(${p.id})">✏️ ${confirmed ? 'Edit' : 'Set'}</span></div></div>
                <div class="detail-row"><div class="detail-label">Assignment:</div><div>${p['Assignment Type']}</div></div>
                <div class="action-buttons">
                    <button class="action-btn action-btn--inject" data-id="${p.id}" data-action="inject">💉 Injection (${left})</button>
                    ${currentTab === 'pending' || currentTab === 'archived' ?
                        `<button class="action-btn action-btn--move" data-id="${p.id}" data-action="move">⟳ Move</button>` :
                        `<button class="action-btn action-btn--pending" data-id="${p.id}" data-action="pending">⏳ Pending</button>`
                    }
                    <button class="action-btn action-btn--edit" data-id="${p.id}" data-action="edit">✎ Edit</button>
                    <button class="action-btn action-btn--delete" data-id="${p.id}" data-action="delete">🗑 Delete</button>
                </div>
            </div>
        </div>
    `;
}

function renderCurrentTab() {
    if (currentTab === 'report') {
        document.getElementById('patientList').style.display = 'none';
        document.getElementById('reportView').style.display = 'block';
        return;
    }
    document.getElementById('patientList').style.display = 'flex';
    document.getElementById('reportView').style.display = 'none';
    const filtered = getFilteredPatients();
    if (!filtered.length) {
        document.getElementById('patientList').innerHTML = '<div class="empty-state"><div class="empty-state__icon">👥</div><p>No patients in this tab</p></div>';
        return;
    }
    const grouped = {};
    filtered.forEach(p => {
        const d = formatDisplayDate(p['Due Date']);
        if (!grouped[d]) grouped[d] = [];
        grouped[d].push(p);
    });
    let html = '';
    for (let date of Object.keys(grouped).sort((a, b) => new Date(a) - new Date(b))) {
        html += `<div class="date-separator">📅 ${date}</div>`;
        grouped[date].forEach(p => html += renderPatientCard(p));
    }
    document.getElementById('patientList').innerHTML = html;
    attachEvents();
}

function attachEvents() {
    document.querySelectorAll('.patient-card').forEach(card => {
        const exp = card.querySelector('.expanded-view');
        card.addEventListener('click', e => {
            if (e.target.tagName !== 'BUTTON' && !e.target.classList.contains('edit-icon')) {
                const show = exp.style.display === 'block';
                exp.style.display = show ? 'none' : 'block';
                card.classList.toggle('expanded', !show);
            }
        });
    });
    document.querySelectorAll('.action-icon--call').forEach(btn => btn.addEventListener('click', e => {
        e.stopPropagation();
        window.location.href = `tel:${btn.dataset.phone}`;
    }));
    document.querySelectorAll('.action-icon--map').forEach(btn => btn.addEventListener('click', e => {
        e.stopPropagation();
        window.open(`https://maps.google.com/?q=${encodeURIComponent(btn.dataset.address)}`);
    }));
    document.querySelectorAll('[data-action="inject"]').forEach(btn => btn.addEventListener('click', e => {
        e.stopPropagation();
        showInjectionModal(parseInt(btn.dataset.id));
    }));
    document.querySelectorAll('[data-action="pending"]').forEach(btn => btn.addEventListener('click', e => {
        e.stopPropagation();
        if (confirm('Mark as pending?')) markPending(parseInt(btn.dataset.id));
    }));
    document.querySelectorAll('[data-action="move"]').forEach(btn => btn.addEventListener('click', e => {
        e.stopPropagation();
        moveToAllPatients(parseInt(btn.dataset.id));
    }));
    document.querySelectorAll('[data-action="edit"]').forEach(btn => btn.addEventListener('click', e => {
        e.stopPropagation();
        openEditModal(parseInt(btn.dataset.id));
    }));
    document.querySelectorAll('[data-action="delete"]').forEach(btn => btn.addEventListener('click', e => {
        e.stopPropagation();
        if (confirm('Delete permanently?')) deletePatient(parseInt(btn.dataset.id));
    }));
}

// ========== MODAL FUNCTIONS ==========
function openAddModal() {
    currentEditId = null;
    document.getElementById('patientForm').reset();
    document.getElementById('deletePatientBtn').style.display = 'none';
    document.getElementById('dueDate').value = getTodayLocal();
    document.getElementById('totalDoses').value = 4;
    document.getElementById('dosesRemaining').value = 4;
    document.getElementById('patientModal').style.display = 'block';
}

function openEditModal(id) {
    const p = patients.find(p => p.id === id);
    if (!p) return;
    currentEditId = id;
    document.getElementById('modalTitle').innerText = 'Edit Patient';
    document.getElementById('patientName').value = p['Patient Name'];
    document.getElementById('fileNumber').value = p['File Number'];
    document.getElementById('address').value = p['Address'] || '';
    document.getElementById('phone1').value = p['Phone 1'] || '';
    document.getElementById('phone2').value = p['Phone 2'] || '';
    document.getElementById('dosePrescribed').value = p['Dose Prescribed'] || '7.5';
    document.getElementById('totalDoses').value = p['Total Doses'];
    document.getElementById('dosesRemaining').value = p['Doses Remaining'];
    document.getElementById('prevInjSite').value = p['Previous Injection Site'] || '';
    document.getElementById('injSite').value = p['Injection Site'] || '';
    document.getElementById('dueDate').value = p['Due Date'] || '';
    document.getElementById('appointmentDateTime').value = p['Appointment Date & Time'] || '';
    document.getElementById('prevInjDates').value = p['Previous Injection Dates'] || '';
    document.getElementById('assignmentType').value = p['Assignment Type'];
    document.getElementById('specialInstructions').value = p['Special Instructions'] || '';
    document.getElementById('adverseEffects').value = p['Adverse Effects Comments'] || '';
    document.getElementById('deletePatientBtn').style.display = 'block';
    document.getElementById('patientModal').style.display = 'block';
}

async function savePatientModal() {
    const fn = document.getElementById('fileNumber').value.trim();
    if (!fn) {
        alert('File number required');
        return;
    }
    if (!currentEditId && patients.find(p => p['File Number'] === fn)) {
        alert('File number exists');
        return;
    }
    const data = {
        'Patient Name': document.getElementById('patientName').value,
        'File Number': fn,
        'Address': document.getElementById('address').value,
        'Phone 1': document.getElementById('phone1').value,
        'Phone 2': document.getElementById('phone2').value,
        'Dose Prescribed': document.getElementById('dosePrescribed').value,
        'Total Doses': document.getElementById('totalDoses').value,
        'Doses Remaining': document.getElementById('dosesRemaining').value,
        'Previous Injection Site': document.getElementById('prevInjSite').value,
        'Injection Site': document.getElementById('injSite').value,
        'Due Date': document.getElementById('dueDate').value,
        'Appointment Date & Time': document.getElementById('appointmentDateTime').value || null,
        'Previous Injection Dates': document.getElementById('prevInjDates').value,
        'Assignment Type': document.getElementById('assignmentType').value,
        'Special Instructions': document.getElementById('specialInstructions').value,
        'Adverse Effects Comments': document.getElementById('adverseEffects').value,
        'File Status': 'Active',
        'Injection Administered': false,
        'Appointment Confirmed': false,
        'Pending': false,
        'Archived': false
    };
    let ok;
    if (currentEditId) {
        data.id = currentEditId;
        ok = await updatePatient(data);
    } else {
        ok = await addPatient(data);
    }
    if (ok) {
        closeModal();
        alert('Saved');
    }
}

function closeModal() {
    document.getElementById('patientModal').style.display = 'none';
    currentEditId = null;
}

function showConfirmDialog(msg, cb) {
    document.getElementById('confirmMessage').innerText = msg;
    document.getElementById('confirmModal').style.display = 'block';
    pendingConfirmCallback = cb;
}

// ========== IMPORT/EXPORT/REPORT ==========
function exportJSON() {
    const blob = new Blob([JSON.stringify(patients, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `backup_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    alert(`Exported ${patients.length} patients`);
}

function exportCSV() {
    if (!patients.length) return;
    const headers = ['Patient Name', 'File Number', 'Address', 'Phone 1', 'Phone 2', 'Dose Prescribed', 'Total Doses', 'Doses Remaining', 'Due Date', 'Assignment Type', 'Special Instructions'];
    const rows = [headers.join(',')];
    patients.forEach(p => {
        rows.push(headers.map(h => {
            let v = p[h] || '';
            if (v.includes(',')) v = `"${v}"`;
            return v;
        }).join(','));
    });
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `patients_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    alert('Exported');
}

function importCSV(file) {
    const r = new FileReader();
    r.onload = async e => {
        const rows = e.target.result.split('\n');
        const headers = rows[0].split(',').map(h => h.trim().replace(/"/g, ''));
        let cnt = 0;
        for (let i = 1; i < rows.length; i++) {
            if (!rows[i].trim()) continue;
            const vals = rows[i].split(',').map(v => v.trim().replace(/"/g, ''));
            const p = {};
            headers.forEach((h, idx) => p[h] = vals[idx] || '');
            if (p['Patient Name'] && !patients.find(ex => ex['File Number'] === p['File Number'])) {
                await addPatient({
                    'Patient Name': p['Patient Name'],
                    'File Number': p['File Number'],
                    'Address': p['Address'] || '',
                    'Phone 1': p['Phone 1'] || '',
                    'Phone 2': p['Phone 2'] || '',
                    'Dose Prescribed': p['Dose Prescribed'] || '7.5',
                    'Total Doses': p['Total Doses'] || '4',
                    'Doses Remaining': p['Doses Remaining'] || '4',
                    'Due Date': getTodayLocal(),
                    'Assignment Type': 'Permanent',
                    'Special Instructions': '',
                    'Adverse Effects Comments': '',
                    'File Status': 'Active',
                    'Injection Administered': false,
                    'Appointment Confirmed': false,
                    'Pending': false,
                    'Archived': false
                });
                cnt++;
            }
        }
        alert(`Imported ${cnt}`);
    };
    r.readAsText(file);
}

function generateReport() {
    const field = document.getElementById('reportField').value;
    const cond = document.getElementById('reportCondition').value;
    const val = document.getElementById('reportValue').value.toLowerCase();
    let filtered = patients.filter(p => {
        let fv = p[field];
        if (field === 'due_date') {
            if (!fv) return false;
            if (cond === 'equals') return fv === val;
            if (cond === 'greater') return fv > val;
            if (cond === 'less') return fv < val;
        } else if (field === 'dose_prescribed') {
            if (cond === 'equals') return fv === val;
            if (cond === 'greater') return parseFloat(fv) > parseFloat(val);
            if (cond === 'less') return parseFloat(fv) < parseFloat(val);
        } else if (field === 'doses_remaining') {
            const rem = parseInt(fv) || 0;
            const v = parseInt(val);
            if (cond === 'equals') return rem === v;
            if (cond === 'greater') return rem > v;
            if (cond === 'less') return rem < v;
        } else {
            fv = String(fv || '').toLowerCase();
            if (cond === 'equals') return fv === val;
            if (cond === 'contains') return fv.includes(val);
        }
        return false;
    });
    if (!filtered.length) {
        document.getElementById('reportOutput').innerHTML = '<div class="empty-state">No matches</div>';
        return;
    }
    let html = `<div style="background:white;border-radius:1rem;padding:1rem"><strong>${filtered.length} found</strong><button onclick="exportReportToCSV()" class="btn btn--secondary" style="margin-left:0.75rem">📥 Export</button>`;
    const grouped = {};
    filtered.forEach(p => {
        const d = formatDisplayDate(p['Due Date']);
        if (!grouped[d]) grouped[d] = [];
        grouped[d].push(p);
    });
    Object.keys(grouped).sort().forEach(date => {
        html += `<div class="date-separator" style="margin-top:1rem">📅 ${date}</div>`;
        grouped[date].forEach(p => {
            html += `<div class="report-item" onclick="openEditModal(${p.id})"><div class="report-item__title"><strong>${escapeHtml(p['Patient Name'])}</strong> #${escapeHtml(p['File Number'])}</div><div class="report-item__subtitle">💊 ${p['Dose Prescribed']}mg</div></div>`;
        });
    });
    html += `</div>`;
    document.getElementById('reportOutput').innerHTML = html;
    window.lastReport = filtered;
}

function exportReportToCSV() {
    if (!window.lastReport || !window.lastReport.length) return;
    const headers = ['Patient Name', 'File Number', 'Phone 1', 'Address', 'Dose Prescribed', 'Doses Remaining', 'Due Date'];
    const rows = [headers.join(',')];
    window.lastReport.forEach(p => {
        rows.push(headers.map(h => {
            let v = p[h] || '';
            if (v.includes(',')) v = `"${v}"`;
            return v;
        }).join(','));
    });
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `report.csv`;
    a.click();
}

function quickReport(type) {
    let field, cond, val;
    if (type === 'dueToday') {
        field = 'due_date';
        cond = 'equals';
        val = getTodayLocal();
    } else if (type === 'noRepeatsLeft') {
        field = 'doses_remaining';
        cond = 'equals';
        val = '0';
    } else if (type === 'pendingPatients') {
        field = 'pending';
        cond = 'equals';
        val = 'true';
    } else if (type === 'tempPatients') {
        field = 'assignment_type';
        cond = 'equals';
        val = 'Temporary';
    } else return;
    document.getElementById('reportField').value = field;
    document.getElementById('reportCondition').value = cond;
    document.getElementById('reportValue').value = val;
    generateReport();
}

function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]));
}

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', async () => {
    const ok = await initSupabase();
    if (ok) await loadPatients();

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTab = btn.dataset.tab;
        renderCurrentTab();
    }));

    // Search
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', e => {
        if (currentTab !== 'report') {
            searchQuery = e.target.value.toLowerCase();
            renderCurrentTab();
        }
    });
    document.getElementById('clearSearchBtn').addEventListener('click', () => {
        searchInput.value = '';
        searchQuery = '';
        renderCurrentTab();
    });

    // Refresh
    document.getElementById('refreshBtn').addEventListener('click', () => loadPatients());

    // Add patient
    document.getElementById('addPatientBtn').addEventListener('click', openAddModal);

    // Data import/export
    document.getElementById('importGoogleSheetsBtn').addEventListener('click', importFromGoogleSheets);
    document.getElementById('importCSVBtn').addEventListener('click', () => document.getElementById('csvFileInput').click());
    document.getElementById('csvFileInput').addEventListener('change', e => { if (e.target.files[0]) importCSV(e.target.files[0]); e.target.value = ''; });
    document.getElementById('importPDFBtn').addEventListener('click', () => document.getElementById('pdfFileInput').click());
    document.getElementById('pdfFileInput').addEventListener('change', e => { if (e.target.files[0]) importPDF(e.target.files[0]); e.target.value = ''; });
    document.getElementById('exportJSONBtn').addEventListener('click', exportJSON);
    document.getElementById('exportCSVReportBtn').addEventListener('click', exportCSV);

    // Report
    document.getElementById('generateReportBtn').addEventListener('click', generateReport);
    document.querySelectorAll('.quick-btn').forEach(btn => btn.addEventListener('click', () => quickReport(btn.dataset.quick)));

    // Modal close handlers
    document.querySelectorAll('.modal__close, .close').forEach(c => c.addEventListener('click', closeModal));
    document.querySelectorAll('.close-injection-modal').forEach(c => c.addEventListener('click', closeInjModal));
    document.querySelectorAll('.close-appt').forEach(c => c.addEventListener('click', () => document.getElementById('apptEditModal').style.display = 'none'));
    window.addEventListener('click', e => {
        if (e.target === document.getElementById('patientModal')) closeModal();
        if (e.target === document.getElementById('confirmModal')) document.getElementById('confirmModal').style.display = 'none';
        if (e.target === document.getElementById('apptEditModal')) document.getElementById('apptEditModal').style.display = 'none';
        if (e.target === document.getElementById('injectionModal')) closeInjModal();
    });

    // Form submit
    document.getElementById('patientForm').addEventListener('submit', e => { e.preventDefault(); savePatientModal(); });
    document.getElementById('deletePatientBtn').addEventListener('click', () => {
        if (currentEditId && confirm('Delete?')) deletePatient(currentEditId).then(() => closeModal());
    });

    // Confirmation modal
    document.getElementById('confirmYes').addEventListener('click', () => {
        if (pendingConfirmCallback) pendingConfirmCallback();
        document.getElementById('confirmModal').style.display = 'none';
        pendingConfirmCallback = null;
    });
    document.getElementById('confirmNo').addEventListener('click', () => {
        document.getElementById('confirmModal').style.display = 'none';
        pendingConfirmCallback = null;
    });

    // Injection modal
    document.getElementById('confirmInjectionBtn').addEventListener('click', performInjection);
    document.getElementById('cancelInjectionBtn').addEventListener('click', closeInjModal);

    // Appointment modal
    document.getElementById('saveAppointmentBtn').addEventListener('click', saveAppointmentDate);
    document.getElementById('cancelAppointmentBtn').addEventListener('click', () => document.getElementById('apptEditModal').style.display = 'none');

    // Global exports for onclick handlers
    window.openEditModal = openEditModal;
    window.openAppointmentEditor = openAppointmentEditor;
    window.exportReportToCSV = exportReportToCSV;
});