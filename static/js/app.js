/**
 * ═══════════════════════════════════════════════
 *  Campus Placement System — Frontend Logic
 * ═══════════════════════════════════════════════
 * 
 * This file is organized into clear sections:
 *  1. WebGL Shader Background (animated hero)
 *  2. API Client (fetch requests to Flask)
 *  3. UI Renderers (draw cards, tables, stats)
 *  4. Modal Management (open/close popups)
 *  5. Form Handlers (submit data to API)
 *  6. Toast Notifications (success/error msgs)
 *  7. Navigation & Scrolling
 *  8. App Initialization
 */

// ═══════════════════════════════════════════════
//  1. WEBGL SHADER BACKGROUND
//     Renders the animated cosmic background
//     on the hero section's <canvas> element.
// ═══════════════════════════════════════════════

// The GLSL fragment shader source — creates the cosmic fire effect
const SHADER_SOURCE = `#version 300 es
precision highp float;
out vec4 O;
uniform vec2 resolution;
uniform float time;
#define FC gl_FragCoord.xy
#define T time
#define R resolution
#define MN min(R.x,R.y)
float rnd(vec2 p){p=fract(p*vec2(12.9898,78.233));p+=dot(p,p+34.56);return fract(p.x*p.y);}
float noise(in vec2 p){vec2 i=floor(p),f=fract(p),u=f*f*(3.-2.*f);float a=rnd(i),b=rnd(i+vec2(1,0)),c=rnd(i+vec2(0,1)),d=rnd(i+1.);return mix(mix(a,b,u.x),mix(c,d,u.x),u.y);}
float fbm(vec2 p){float t=.0,a=1.;mat2 m=mat2(1.,-.5,.2,1.2);for(int i=0;i<5;i++){t+=a*noise(p);p*=2.*m;a*=.5;}return t;}
float clouds(vec2 p){float d=1.,t=.0;for(float i=.0;i<3.;i++){float a=d*fbm(i*10.+p.x*.2+.2*(1.+i)*p.y+d+i*i+p);t=mix(t,d,a);d=a;p*=2./(i+1.);}return t;}
void main(void){
  vec2 uv=(FC-.5*R)/MN,st=uv*vec2(2,1);
  vec3 col=vec3(0);
  float bg=clouds(vec2(st.x+T*.5,-st.y));
  uv*=1.-.3*(sin(T*.2)*.5+.5);
  for(float i=1.;i<12.;i++){
    uv+=.1*cos(i*vec2(.1+.01*i,.8)+i*i+T*.5+.1*uv.x);
    vec2 p=uv;float d=length(p);
    col+=.00125/d*(cos(sin(i)*vec3(1,2,3))+1.);
    float b=noise(i+p+bg*1.731);
    col+=.002*b/length(max(p,vec2(b*p.x*.02,p.y)));
    col=mix(col,vec3(bg*.25,bg*.137,bg*.05),d);
  }
  O=vec4(col,1);
}`;

// Vertex shader — just draws a full-screen quad
const VERTEX_SOURCE = `#version 300 es
precision highp float;
in vec4 position;
void main(){gl_Position=position;}`;

/**
 * Initialize the WebGL shader on the hero canvas
 * This creates the animated background effect
 */
function initShaderBackground() {
    const canvas = document.getElementById('shader-canvas');
    if (!canvas) return;

    const gl = canvas.getContext('webgl2');
    if (!gl) {
        console.warn('WebGL2 not supported — falling back to gradient bg');
        canvas.style.background = 'linear-gradient(135deg, #0a0a0f, #1a0a00)';
        return;
    }

    // Resize canvas to match screen (accounting for pixel density)
    function resize() {
        const dpr = Math.max(1, 0.5 * window.devicePixelRatio);
        canvas.width = window.innerWidth * dpr;
        canvas.height = window.innerHeight * dpr;
        gl.viewport(0, 0, canvas.width, canvas.height);
    }

    // Compile a GLSL shader and check for errors
    function compileShader(type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            console.error('Shader error:', gl.getShaderInfoLog(shader));
            gl.deleteShader(shader);
            return null;
        }
        return shader;
    }

    // Create shader program by linking vertex + fragment shaders
    const vs = compileShader(gl.VERTEX_SHADER, VERTEX_SOURCE);
    const fs = compileShader(gl.FRAGMENT_SHADER, SHADER_SOURCE);
    if (!vs || !fs) return;

    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        console.error('Program link error:', gl.getProgramInfoLog(program));
        return;
    }

    // Set up a full-screen rectangle (two triangles)
    const vertices = new Float32Array([-1, 1, -1, -1, 1, 1, 1, -1]);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

    const posLoc = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

    // Get uniform locations (variables passed to shader each frame)
    const uResolution = gl.getUniformLocation(program, 'resolution');
    const uTime = gl.getUniformLocation(program, 'time');

    resize();
    window.addEventListener('resize', resize);

    let animationFrameId = null;
    let isVisible = true;

    // Animation loop — runs every frame at ~60fps
    function render(now) {
        if (!isVisible) {
            animationFrameId = null;
            return;
        }
        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.useProgram(program);
        gl.uniform2f(uResolution, canvas.width, canvas.height);
        gl.uniform1f(uTime, now * 0.001); // Convert ms to seconds
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        animationFrameId = requestAnimationFrame(render);
    }

    // IntersectionObserver stops rendering when the Hero is out of view (e.g. while looking at the dashboard)
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            isVisible = entry.isIntersecting;
            if (isVisible && !animationFrameId) {
                animationFrameId = requestAnimationFrame(render);
            }
        });
    }, { threshold: 0.01 });

    const heroSection = document.getElementById('hero');
    if (heroSection) {
        observer.observe(heroSection);
    } else {
        animationFrameId = requestAnimationFrame(render);
    }
}


// ═══════════════════════════════════════════════
//  2. API CLIENT
//     Simple functions to call our Flask API.
//     Each returns a Promise with JSON data.
// ═══════════════════════════════════════════════

const API = {
    // GET request helper
    async get(endpoint) {
        const res = await fetch(endpoint);
        return res.json();
    },

    // POST request helper
    async post(endpoint, data) {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return res.json();
    },

    async patch(endpoint, data) {
        const res = await fetch(endpoint, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return res.json();
    },

    async delete(endpoint) {
        const res = await fetch(endpoint, { method: 'DELETE' });
        return res.json();
    }
};

const APPLICATION_STATUSES = ['Applied', 'Screening', 'Interview', 'Selected', 'Rejected', 'Withdrawn'];

function applicationStatusSelect(status, onchange) {
    return `<select class="application-status-select" onchange="${onchange}">${APPLICATION_STATUSES.map(option => `<option value="${option}" ${option === status ? 'selected' : ''}>${option}</option>`).join('')}</select>`;
}

let activeAuthRole = 'student';
let activeAuthMode = 'login';
let currentUserRole = null;
let editingCompanyId = null;
let editingInterviewId = null;

function selectAuthRole(role) {
    activeAuthRole = role;
    document.querySelectorAll('.auth-role-tab').forEach(tab => tab.classList.toggle('active', tab.dataset.role === role));
    document.getElementById('student-login-field').classList.toggle('hidden', role !== 'student');
    document.getElementById('admin-login-field').classList.toggle('hidden', role !== 'admin');
    document.getElementById('auth-student-id').required = role === 'student';
    document.getElementById('auth-username').required = role === 'admin';
    document.getElementById('student-register-fields').classList.toggle('hidden', role !== 'student');
    document.getElementById('admin-register-fields').classList.toggle('hidden', role !== 'admin');
    document.getElementById('auth-account-id-label').textContent = role === 'student' ? 'Student ID' : 'Admin ID';
    document.getElementById('auth-title').textContent = role === 'student' ? 'Student portal' : 'Admin portal';
    document.getElementById('auth-message').textContent = '';
}

function selectAuthMode(mode) {
    activeAuthMode = mode;
    document.querySelectorAll('.auth-mode-tab').forEach(tab => tab.classList.toggle('active', tab.dataset.mode === mode));
    document.getElementById('auth-login-form').classList.toggle('hidden', mode !== 'login');
    document.getElementById('auth-register-form').classList.toggle('hidden', mode !== 'register');
    document.getElementById('auth-message').textContent = '';
}

function applyRoleUI(role) {
    currentUserRole = role;
    document.body.classList.toggle('student-mode', role === 'student');
    document.body.classList.toggle('admin-mode', role === 'admin');
    document.querySelectorAll('.nav-link').forEach(link => {
        const section = link.dataset.section;
        const hiddenForStudent = ['admins', 'reports'].includes(section);
        link.closest('li').classList.toggle('hidden', role === 'student' && hiddenForStudent);
    });
    document.querySelectorAll('.admin-only-control').forEach(button => {
        button.classList.toggle('hidden', role !== 'admin');
    });
    document.querySelectorAll('#eligibility .form-group').forEach(group => {
        if (role === 'student' && group.querySelector('#elig-student')) group.classList.add('hidden');
    });
    document.getElementById('auth-gate').classList.add('hidden');
}

function showAuthError(message) {
    document.getElementById('auth-message').textContent = message || 'Unable to complete that request.';
}

async function handleLogin(event) {
    event.preventDefault();
    try {
        const result = await API.post('/api/auth/login', {
            role: activeAuthRole,
            student_id: document.getElementById('auth-student-id').value,
            username: document.getElementById('auth-username').value,
            password: document.getElementById('auth-password').value
        });
        if (!result.success) {
            showAuthError(result.message);
            return;
        }
        applyRoleUI(result.role);
        await refreshAll();
    } catch (error) {
        showAuthError('The login request could not be completed. Please try again.');
    }
}

async function handleRegistration(event) {
    event.preventDefault();
    try {
        const isStudent = activeAuthRole === 'student';
        const data = {
        person_id: document.getElementById('auth-person-id').value,
        name: document.getElementById('auth-name').value,
        email: document.getElementById('auth-email').value,
        contact_number: document.getElementById('auth-phone').value,
        password: document.getElementById('auth-register-password').value
        };
        if (isStudent) {
        Object.assign(data, {
            student_id: document.getElementById('auth-account-id').value,
            branch: document.getElementById('auth-branch').value,
            cgpa: document.getElementById('auth-cgpa').value,
            skills: document.getElementById('auth-skills').value
        });
        } else {
        Object.assign(data, {
            admin_id: document.getElementById('auth-account-id').value,
            username: document.getElementById('auth-register-username').value,
            designation: document.getElementById('auth-designation').value
        });
        }
        const result = await API.post(`/api/auth/register/${isStudent ? 'student' : 'admin'}`, data);
        if (!result.success) {
            showAuthError(result.message);
            return;
        }
        selectAuthMode('login');
        if (isStudent) document.getElementById('auth-student-id').value = data.student_id;
        else document.getElementById('auth-username').value = data.username;
        document.getElementById('auth-password').value = data.password;
        document.getElementById('auth-message').textContent = result.message;
        document.getElementById('auth-message').style.color = 'var(--success)';
    } catch (error) {
        showAuthError('The registration request could not be completed. Please check the fields and try again.');
    }
}

async function logout() {
    await API.post('/api/auth/logout', {});
    currentUserRole = null;
    document.body.classList.remove('student-mode', 'admin-mode');
    document.getElementById('auth-gate').classList.remove('hidden');
    selectAuthMode('login');
}


// ═══════════════════════════════════════════════
//  3. UI RENDERERS
//     Functions that fetch data and render
//     HTML cards/tables into the DOM.
// ═══════════════════════════════════════════════

/** Render the dashboard statistics cards */
async function renderStats() {
    const stats = await API.get('/api/stats');
    const grid = document.getElementById('stats-grid');

    const items = [
        { icon: '\ud83d\udc68\u200d\ud83c\udf93', value: stats.total_students, label: 'Total Students' },
        { icon: '\ud83c\udfe2', value: stats.total_companies, label: 'Companies' },
        { icon: '\u2705', value: stats.placed_students, label: 'Placed' },
        { icon: '\u274c', value: stats.not_placed, label: 'Not Placed' },
        { icon: '\ud83d\udcca', value: stats.placement_pct + '%', label: 'Placement Rate' },
        { icon: '\ud83d\udcc5', value: stats.total_drives, label: 'Drives' },
        { icon: '\ud83c\udfa4', value: stats.total_interviews, label: 'Interviews' },
        { icon: '\ud83d\udcb0', value: stats.highest_package + ' LPA', label: 'Highest Package' },
        { icon: '\ud83d\udcc8', value: stats.avg_package + ' LPA', label: 'Avg Package' },
        { icon: '\ud83d\udcdc', value: stats.total_offers, label: 'Total Offers' },
    ];

    grid.innerHTML = items.map(item => `
        <div class="stat-card reveal">
            <div class="stat-icon">${item.icon}</div>
            <div class="stat-value">${item.value}</div>
            <div class="stat-label">${item.label}</div>
        </div>
    `).join('');

    // Render NIET top placements
    renderTopPlacements();
    // Animate NIET institutional counters
    animateCounters();
    observeReveal();
}

/**
 * NIET Top Placements — real data from niet.co.in
 * These are the top placement records for 2025-26
 */
const EATM_TOP_PLACEMENTS = [
    { name: "Sumit Pathak", branch: "CSE", company: "Autodesk", package: "39 LPA" },
    { name: "Varun Gupta", branch: "CSE (AI & ML)", company: "Autodesk", package: "39 LPA" },
    { name: "Aditya Singh", branch: "CSE (DS)", company: "Eightfold.ai", package: "37.53 LPA" },
    { name: "Vanshika Pandey", branch: "CSE", company: "AMD", package: "30 LPA" },
    { name: "Ayush Mani", branch: "CSE (AI & ML)", company: "Juspay", package: "27 LPA" },
    { name: "Ankush Chauhan", branch: "CSE (AI & ML)", company: "Juspay", package: "21 LPA" },
    { name: "Himanshu Pandey", branch: "CSE (AI)", company: "Atlan", package: "20 LPA" },
    { name: "Anmol Srivastava", branch: "CSE", company: "JP Morgan Chase", package: "19.75 LPA" },
    { name: "Onkar Jha", branch: "ECE", company: "Vance", package: "19 LPA" },
    { name: "Saurabh Kumar", branch: "CSE (Regional)", company: "Auditorium Works", package: "14 LPA" },
    { name: "Abhay Kumar", branch: "CSE", company: "Amadeus Lab", package: "12.62 LPA" },
    { name: "Ayush Rawat", branch: "CSE (AIML)", company: "NatWest", package: "12 LPA" },
];

/** Render NIET top placement cards into the dashboard */
function renderTopPlacements() {
    const grid = document.getElementById('top-placements-grid');
    if (!grid) return;

    grid.innerHTML = EATM_TOP_PLACEMENTS.slice(0, 8).map((p, i) => `
        <div class="data-card reveal">
            <div class="placement-rank">#${i + 1}</div>
            <div class="data-card-header">
                <div class="data-card-title">${p.name}</div>
                <span class="data-card-badge badge-package">${p.package}</span>
            </div>
            <div class="data-card-row"><span class="data-card-label">Branch</span><span class="data-card-value">${p.branch}</span></div>
            <div class="data-card-row"><span class="data-card-label">Company</span><span class="data-card-value">${p.company}</span></div>
        </div>
    `).join('');
}

/**
 * Animated counter — counts from 0 to target value
 * Uses IntersectionObserver so it only starts when visible
 */
function animateCounters() {
    const counters = document.querySelectorAll('.counter');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseInt(el.dataset.target);
                const duration = 2000;
                const start = performance.now();

                function update(now) {
                    const elapsed = now - start;
                    const progress = Math.min(elapsed / duration, 1);
                    const eased = 1 - Math.pow(1 - progress, 3);
                    el.textContent = Math.floor(eased * target) + '+';
                    if (progress < 1) requestAnimationFrame(update);
                }
                requestAnimationFrame(update);
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.3 });

    counters.forEach(c => observer.observe(c));
}

/** Render admin cards */
async function renderAdmins() {
    const admins = await API.get('/api/admins');
    const grid = document.getElementById('admins-grid');
    const empty = document.getElementById('admins-empty');

    if (admins.length === 0) {
        grid.innerHTML = '';
        empty.classList.add('visible');
        return;
    }
    empty.classList.remove('visible');

    grid.innerHTML = admins.map(a => `
        <div class="data-card reveal">
            <div class="data-card-header">
                <div class="data-card-title">${a.name}</div>
                <span class="data-card-badge badge-package">${a.designation}</span>
            </div>
            <div class="data-card-row"><span class="data-card-label">Admin ID</span><span class="data-card-value">${a.admin_id}</span></div>
            <div class="data-card-row"><span class="data-card-label">Username</span><span class="data-card-value">${a.username}</span></div>
            <div class="data-card-row"><span class="data-card-label">Email</span><span class="data-card-value">${a.email}</span></div>
            <div class="data-card-row"><span class="data-card-label">Phone</span><span class="data-card-value">${a.contact_number}</span></div>
        </div>
    `).join('');

    observeReveal();
}

/** Render student cards */
async function renderStudents() {
    const students = await API.get('/api/students');
    const grid = document.getElementById('students-grid');
    const empty = document.getElementById('students-empty');

    if (students.length === 0) {
        grid.innerHTML = '';
        empty.classList.add('visible');
        return;
    }
    empty.classList.remove('visible');

    grid.innerHTML = students.map(s => `
        <div class="data-card reveal">
            <div class="data-card-header">
                <div class="data-card-title">${s.name}</div>
                <span class="data-card-badge ${s.placement_status === 'Placed' ? 'badge-placed' : 'badge-not-placed'}">
                    ${s.placement_status}
                </span>
            </div>
            <div class="data-card-row"><span class="data-card-label">Student ID</span><span class="data-card-value">${s.student_id}</span></div>
            <div class="data-card-row"><span class="data-card-label">Branch</span><span class="data-card-value">${s.branch}</span></div>
            <div class="data-card-row"><span class="data-card-label">CGPA</span><span class="data-card-value">${s.cgpa}</span></div>
            <div class="data-card-row"><span class="data-card-label">Email</span><span class="data-card-value">${s.email}</span></div>
            ${currentUserRole === 'admin' ? `<div class="data-card-row"><span class="data-card-label">Applied Drives</span><span class="data-card-value">${s.applied_drives && s.applied_drives.length ? s.applied_drives.map(application => `${application.drive_id} (${application.status})`).join(', ') : 'None'}</span></div>` : ''}
            ${currentUserRole === 'admin' ? `<div class="data-card-row"><span class="data-card-label">Placement Applications</span><span class="data-card-value">${s.applied_placements && s.applied_placements.length ? s.applied_placements.map(application => `${application.company_name} (${application.status})`).join(', ') : 'None'}</span></div>` : ''}
            ${s.skills && s.skills.length > 0 ? `
                <div class="skills-list">
                    ${s.skills.map(sk => `<span class="skill-tag">${sk}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');

    observeReveal();
}

/** Render company cards */
async function renderCompanies() {
    const companies = await API.get('/api/companies');
    const grid = document.getElementById('companies-grid');
    const empty = document.getElementById('companies-empty');

    if (companies.length === 0) {
        grid.innerHTML = '';
        empty.classList.add('visible');
        return;
    }
    empty.classList.remove('visible');

    grid.innerHTML = companies.map(c => `
        <div class="data-card reveal">
            <div class="data-card-header">
                <div class="data-card-title">${c.company_name}</div>
                <span class="data-card-badge badge-package">${c.package} LPA</span>
            </div>
            <div class="data-card-row"><span class="data-card-label">Company ID</span><span class="data-card-value">${c.company_id}</span></div>
            <div class="data-card-row"><span class="data-card-label">Job Role</span><span class="data-card-value">${c.job_role}</span></div>
            <div class="data-card-row"><span class="data-card-label">Min CGPA</span><span class="data-card-value">${c.eligibility_cgpa}</span></div>
            ${currentUserRole === 'admin' ? `<button type="button" class="btn btn-glass admin-only-control" onclick="openCompanyEdit('${c.company_id}')">Edit Company</button>` : ''}
            ${currentUserRole === 'student' ? `<div class="application-action">${c.has_applied ? `<span class="data-card-badge badge-scheduled">${c.application_status || 'Applied'}</span>` : `<button type="button" class="btn btn-primary" onclick="handlePlacementApplication('${c.company_id}', this)">Apply for Placement</button>`}</div>` : ''}
            ${currentUserRole === 'admin' && c.applicants && c.applicants.length ? `<div class="applicant-list"><span class="data-card-label">Applicants</span>${c.applicants.map(applicant => `<div class="applicant-row"><span>${applicant.name} (${applicant.student_id})</span>${applicationStatusSelect(applicant.status, `updateCompanyApplication('${c.company_id}', '${applicant.student_id}', this.value)`)}</div>`).join('')}</div>` : ''}
        </div>
    `).join('');

    observeReveal();
}

async function handlePlacementApplication(companyId, button) {
    button.disabled = true;
    const result = await API.post(`/api/companies/${encodeURIComponent(companyId)}/apply`, {});
    if (result.success) {
        button.textContent = 'Applied';
        showToast(result.message, 'success');
        return;
    }
    button.disabled = false;
    showToast(result.message, 'error');
}

function openCompanyModal() {
    editingCompanyId = null;
    document.getElementById('company-modal-title').textContent = 'Register New Company';
    document.getElementById('company-submit-button').textContent = 'Register Company';
    document.getElementById('c-cid').disabled = false;
    openModal('company-modal');
}

async function openCompanyEdit(companyId) {
    const companies = await API.get('/api/companies');
    const company = companies.find(item => item.company_id === companyId);
    if (!company) return;
    editingCompanyId = companyId;
    document.getElementById('company-modal-title').textContent = 'Edit Company Profile';
    document.getElementById('company-submit-button').textContent = 'Save Company Changes';
    document.getElementById('c-cid').value = company.company_id;
    document.getElementById('c-cid').disabled = true;
    document.getElementById('c-name').value = company.company_name;
    document.getElementById('c-package').value = company.package;
    document.getElementById('c-cgpa').value = company.eligibility_cgpa;
    document.getElementById('c-role').value = company.job_role;
    openModal('company-modal');
}

/** Render placement drive cards */
async function renderDrives() {
    const drives = await API.get('/api/drives');
    const grid = document.getElementById('drives-grid');
    const empty = document.getElementById('drives-empty');

    if (drives.length === 0) {
        grid.innerHTML = '';
        empty.classList.add('visible');
        return;
    }
    empty.classList.remove('visible');

    grid.innerHTML = drives.map(d => `
        <div class="data-card reveal">
            <div class="data-card-header">
                <div class="data-card-title">Drive: ${d.drive_id}</div>
                <span class="data-card-badge badge-scheduled">📅 ${d.drive_date}</span>
            </div>
            <div class="data-card-row"><span class="data-card-label">Company</span><span class="data-card-value">${d.company}</span></div>
            <div class="data-card-row"><span class="data-card-label">Eligible Students</span><span class="data-card-value">${d.eligible_students ? d.eligible_students.length : 0}</span></div>
            ${currentUserRole === 'student' ? `<div class="application-action">${d.has_applied ? `<span class="data-card-badge badge-scheduled">${d.application_status || 'Applied'}</span>` : `<button type="button" class="btn btn-primary" onclick="handleDriveApplication('${d.drive_id}', this)">Apply for Drive</button>`}</div>` : ''}
            ${currentUserRole === 'admin' && d.applicants && d.applicants.length ? `<div class="applicant-list"><span class="data-card-label">Applicants</span>${d.applicants.map(applicant => `<div class="applicant-row"><span>${applicant.name} (${applicant.student_id})</span>${applicationStatusSelect(applicant.status, `updateDriveApplication('${d.drive_id}', '${applicant.student_id}', this.value)`)}</div>`).join('')}</div>` : ''}
        </div>
    `).join('');

    observeReveal();
}

async function handleDriveApplication(driveId, button) {
    button.disabled = true;
    const result = await API.post(`/api/drives/${encodeURIComponent(driveId)}/apply`, {});
    if (result.success) {
        button.textContent = 'Applied';
        showToast(result.message, 'success');
        return;
    }
    button.disabled = false;
    showToast(result.message, 'error');
}

async function updateCompanyApplication(companyId, studentId, status) {
    const result = await API.patch(`/api/companies/${encodeURIComponent(companyId)}/applications/${encodeURIComponent(studentId)}`, { status });
    showToast(result.message, result.success ? 'success' : 'error');
}

async function updateDriveApplication(driveId, studentId, status) {
    const result = await API.patch(`/api/drives/${encodeURIComponent(driveId)}/applications/${encodeURIComponent(studentId)}`, { status });
    showToast(result.message, result.success ? 'success' : 'error');
}

/** Render interview table rows */
async function renderInterviews() {
    const interviews = await API.get('/api/interviews');
    const tbody = document.getElementById('interviews-tbody');
    const empty = document.getElementById('interviews-empty');
    const table = document.getElementById('interviews-table');

    if (interviews.length === 0) {
        tbody.innerHTML = '';
        table.style.display = 'none';
        empty.classList.add('visible');
        return;
    }
    table.style.display = 'table';
    empty.classList.remove('visible');

    tbody.innerHTML = interviews.map(i => `
        <tr>
            <td>${i.interview_id}</td>
            <td>${i.student_name} (${i.student})</td>
            <td>${i.company_name} (${i.company})</td>
            <td>${i.interview_date}</td>
            <td><span class="data-card-badge badge-scheduled">${i.status}</span></td>
            ${currentUserRole === 'admin' ? `<td class="table-actions"><button type="button" class="btn btn-glass" onclick='openInterviewEdit(${JSON.stringify(i)})'>Edit</button><button type="button" class="btn btn-danger" onclick="deleteInterview('${i.interview_id}')">Delete</button></td>` : ''}
        </tr>
    `).join('');
}

async function openInterviewEdit(interview) {
    editingInterviewId = interview.interview_id;
    document.getElementById('interview-modal-title').textContent = 'Edit Interview';
    document.getElementById('interview-submit-button').textContent = 'Save Interview Changes';
    await openModal('interview-modal');
    document.getElementById('i-iid').value = interview.interview_id;
    document.getElementById('i-iid').disabled = true;
    document.getElementById('i-student').value = interview.student;
    document.getElementById('i-company').value = interview.company;
    document.getElementById('i-date').value = interview.interview_date;
    document.getElementById('i-status').value = interview.status;
}

async function deleteInterview(interviewId) {
    if (!window.confirm(`Delete interview ${interviewId}?`)) return;
    const result = await API.delete(`/api/interviews/${encodeURIComponent(interviewId)}`);
    showToast(result.message, result.success ? 'success' : 'error');
    if (result.success) refreshAll();
}

/** Render job offer cards */
async function renderOffers() {
    const offers = await API.get('/api/offers');
    const grid = document.getElementById('offers-grid');
    const empty = document.getElementById('offers-empty');

    if (offers.length === 0) {
        grid.innerHTML = '';
        empty.classList.add('visible');
        return;
    }
    empty.classList.remove('visible');

    grid.innerHTML = offers.map(o => `
        <div class="data-card reveal">
            <div class="data-card-header">
                <div class="data-card-title">Offer: ${o.offer_id}</div>
                <span class="data-card-badge badge-package">${o.package} LPA</span>
            </div>
            <div class="data-card-row"><span class="data-card-label">Student</span><span class="data-card-value">${o.student}</span></div>
            <div class="data-card-row"><span class="data-card-label">Company</span><span class="data-card-value">${o.company}</span></div>
            <div class="data-card-row"><span class="data-card-label">Status</span><span class="data-card-value">${o.offer_status}</span></div>
        </div>
    `).join('');

    observeReveal();
}

/** Populate dropdown selects for eligibility, modals */
async function populateDropdowns() {
    const students = await API.get('/api/students');
    const companies = await API.get('/api/companies');

    // All student select elements
    const studentSelects = ['elig-student', 'i-student', 'o-student'];
    studentSelects.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = '<option value="">Select Student</option>' +
                students.map(s => `<option value="${s.student_id}">${s.name} (${s.student_id})</option>`).join('');
        }
    });

    // All company select elements
    const companySelects = ['elig-company', 'i-company', 'o-company', 'd-company'];
    companySelects.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = '<option value="">Select Company</option>' +
                companies.map(c => `<option value="${c.company_id}">${c.company_name} (${c.company_id})</option>`).join('');
        }
    });
}


// ═══════════════════════════════════════════════
//  4. MODAL MANAGEMENT
// ═══════════════════════════════════════════════

async function openModal(modalId) {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.classList.remove('active');
    });
    const targetModal = document.getElementById(modalId);
    if (targetModal) {
        targetModal.classList.add('active');
    }
    await populateDropdowns(); // Refresh dropdown options
}

function closeModal(modalId) {
    const targetModal = document.getElementById(modalId);
    if (targetModal) {
        targetModal.classList.remove('active');
    }
}

// Close modal when clicking overlay background
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});


// ═══════════════════════════════════════════════
//  5. FORM HANDLERS
//     Each handler reads form inputs, sends
//     data to the API, and refreshes the UI.
// ═══════════════════════════════════════════════

async function handleAdminSubmit(e) {
    e.preventDefault();
    const data = {
        person_id: document.getElementById('a-pid').value,
        admin_id: document.getElementById('a-aid').value,
        name: document.getElementById('a-name').value,
        email: document.getElementById('a-email').value,
        contact_number: document.getElementById('a-phone').value,
        username: document.getElementById('a-username').value,
        password: document.getElementById('a-password').value,
        designation: document.getElementById('a-designation').value
    };
    const result = await API.post('/api/admins', data);
    if (result.success) {
        showToast(result.message, 'success');
        closeModal('admin-modal');
        e.target.reset();
        refreshAll();
    } else {
        showToast(result.message, 'error');
    }
}

async function handleStudentSubmit(e) {
    e.preventDefault(); // Prevent page reload
    const data = {
        person_id: document.getElementById('s-pid').value,
        student_id: document.getElementById('s-sid').value,
        name: document.getElementById('s-name').value,
        email: document.getElementById('s-email').value,
        contact_number: document.getElementById('s-phone').value,
        branch: document.getElementById('s-branch').value,
        cgpa: document.getElementById('s-cgpa').value,
        skills: document.getElementById('s-skills').value
    };
    const result = await API.post('/api/students', data);
    if (result.success) {
        showToast(result.message, 'success');
        closeModal('student-modal');
        e.target.reset();
        refreshAll();
    } else {
        showToast(result.message, 'error');
    }
}

async function handleCompanySubmit(e) {
    e.preventDefault();
    const data = {
        company_id: document.getElementById('c-cid').value,
        company_name: document.getElementById('c-name').value,
        package: document.getElementById('c-package').value,
        eligibility_cgpa: document.getElementById('c-cgpa').value,
        job_role: document.getElementById('c-role').value
    };
    const result = editingCompanyId
        ? await API.patch(`/api/companies/${encodeURIComponent(editingCompanyId)}`, data)
        : await API.post('/api/companies', data);
    if (result.success) {
        showToast(result.message, 'success');
        closeModal('company-modal');
        e.target.reset();
        editingCompanyId = null;
        document.getElementById('c-cid').disabled = false;
        refreshAll();
    } else {
        showToast(result.message, 'error');
    }
}

async function handleDriveSubmit(e) {
    e.preventDefault();
    const data = {
        drive_id: document.getElementById('d-did').value,
        company: document.getElementById('d-company').value,
        drive_date: document.getElementById('d-date').value
    };
    const result = await API.post('/api/drives', data);
    if (result.success) {
        showToast(result.message, 'success');
        closeModal('drive-modal');
        e.target.reset();
        refreshAll();
    } else {
        showToast(result.message, 'error');
    }
}

async function handleInterviewSubmit(e) {
    e.preventDefault();
    const data = {
        interview_id: document.getElementById('i-iid').value,
        student: document.getElementById('i-student').value,
        company: document.getElementById('i-company').value,
        interview_date: document.getElementById('i-date').value,
        status: document.getElementById('i-status').value
    };
    const result = editingInterviewId
        ? await API.patch(`/api/interviews/${encodeURIComponent(editingInterviewId)}`, data)
        : await API.post('/api/interviews', data);
    if (result.success) {
        showToast(result.message, 'success');
        closeModal('interview-modal');
        e.target.reset();
        editingInterviewId = null;
        document.getElementById('i-iid').disabled = false;
        refreshAll();
    } else {
        showToast(result.message, 'error');
    }
}

async function handleOfferSubmit(e) {
    e.preventDefault();
    const data = {
        offer_id: document.getElementById('o-oid').value,
        student: document.getElementById('o-student').value,
        company: document.getElementById('o-company').value,
        package: document.getElementById('o-package').value
    };
    const result = await API.post('/api/offers', data);
    if (result.success) {
        showToast(result.message, 'success');
        closeModal('offer-modal');
        e.target.reset();
        refreshAll();
    } else {
        showToast(result.message, 'error');
    }
}

/** Eligibility check (not a modal — inline form) */
async function checkEligibility() {
    const studentId = document.getElementById('elig-student').value;
    const companyId = document.getElementById('elig-company').value;

    if (!studentId || !companyId) {
        showToast('Please select both student and company', 'error');
        return;
    }

    const result = await API.post('/api/eligibility', {
        student_id: studentId,
        company_id: companyId
    });

    const div = document.getElementById('eligibility-result');
    div.classList.remove('hidden', 'eligible', 'not-eligible');
    div.classList.add(result.eligible ? 'eligible' : 'not-eligible');
    div.textContent = result.message;
}

/** Search student by ID */
async function searchStudent() {
    const query = document.getElementById('student-search').value.trim();
    if (query.length === 0) {
        renderStudents(); // Show all when search is empty
        return;
    }

    const result = await API.get(`/api/students/search/${query}`);
    const grid = document.getElementById('students-grid');

    if (result.success) {
        const s = result.student;
        grid.innerHTML = `
            <div class="data-card">
                <div class="data-card-header">
                    <div class="data-card-title">${s.name}</div>
                    <span class="data-card-badge ${s.placement_status === 'Placed' ? 'badge-placed' : 'badge-not-placed'}">${s.placement_status}</span>
                </div>
                <div class="data-card-row"><span class="data-card-label">Student ID</span><span class="data-card-value">${s.student_id}</span></div>
                <div class="data-card-row"><span class="data-card-label">Branch</span><span class="data-card-value">${s.branch}</span></div>
                <div class="data-card-row"><span class="data-card-label">CGPA</span><span class="data-card-value">${s.cgpa}</span></div>
                <div class="data-card-row"><span class="data-card-label">Email</span><span class="data-card-value">${s.email}</span></div>
            </div>`;
    } else {
        grid.innerHTML = '<div class="empty-state visible">No student found with that ID.</div>';
    }
}

/** Generate CSV report */
async function generateReport() {
    const result = await API.post('/api/reports');
    showToast(result.message, result.success ? 'success' : 'error');
}

/** Save data manually */
async function saveData() {
    const result = await API.post('/api/data/save');
    showToast(result.message, result.success ? 'success' : 'error');
}

/** Load data manually */
async function loadData() {
    const result = await API.post('/api/data/load');
    if (result.success) {
        showToast(result.message, 'success');
        refreshAll();
    } else {
        showToast(result.message, 'error');
    }
}


// ═══════════════════════════════════════════════
//  6. TOAST NOTIFICATIONS
//     Shows temporary success/error messages
// ═══════════════════════════════════════════════

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}


// ═══════════════════════════════════════════════
//  7. NAVIGATION & SCROLLING
// ═══════════════════════════════════════════════

/** Smooth scroll to a section */
function scrollToSection(sectionId) {
    document.getElementById(sectionId).scrollIntoView({ behavior: 'smooth' });
}

/** Highlight active nav link based on scroll position */
function setupNavHighlighting() {
    const links = document.querySelectorAll('.nav-link');

    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = link.dataset.section;
            scrollToSection(sectionId);
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });
}

/** Use IntersectionObserver to add scroll reveal animations */
function observeReveal() {
    const elements = document.querySelectorAll('.reveal:not(.visible)');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                // Stagger animation by adding delay
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, index * 80);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    elements.forEach(el => observer.observe(el));
}


// ═══════════════════════════════════════════════
//  8. BEAMS BACKGROUND ANIMATION
//     Renders animated light beams behind the
//     dashboard area — converted from React to
//     vanilla JS for our no-framework stack.
// ═══════════════════════════════════════════════

function createBeam(width, height) {
    const angle = -35 + Math.random() * 10;
    return {
        x: Math.random() * width * 1.5 - width * 0.25,
        y: Math.random() * height * 1.5 - height * 0.25,
        width: 10 + Math.random() * 20, // Scaled down for smaller canvas resolution
        length: height * 2.5,
        angle: angle,
        speed: 0.2 + Math.random() * 0.4, // Scaled down speed for smaller resolution
        opacity: 0.12 + Math.random() * 0.16,
        hue: 190 + Math.random() * 70,
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: 0.02 + Math.random() * 0.03,
    };
}

function initBeamsBackground() {
    const canvas = document.getElementById('beams-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const BEAM_COUNT = 20; // Reduced from 30 to 20 for extra speed
    let beams = [];

    function resizeCanvas() {
        // Optimize resolution: lock canvas size to a low, performance-friendly resolution.
        // CSS handles stretching and hardware-accelerated blurring, saving millions of operations/sec.
        canvas.width = 512;
        canvas.height = 512;
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        
        beams = Array.from({ length: BEAM_COUNT }, () =>
            createBeam(canvas.width, canvas.height)
        );
    }

    resizeCanvas();
    // No need to resize internal resolution on window resize, just stretch it with CSS!
    window.addEventListener('resize', () => {
        // Keep style stretching responsive, but don't re-create canvas buffer
        canvas.style.width = '100%';
        canvas.style.height = '100%';
    });

    function resetBeam(beam, index) {
        const column = index % 3;
        const spacing = canvas.width / 3;
        beam.y = canvas.height + 100;
        beam.x = column * spacing + spacing / 2 + (Math.random() - 0.5) * spacing * 0.5;
        beam.width = 30 + Math.random() * 40; // Scaled down width
        beam.speed = 0.15 + Math.random() * 0.2; // Scaled down speed
        beam.hue = 190 + (index * 70) / BEAM_COUNT;
        beam.opacity = 0.2 + Math.random() * 0.1;
        return beam;
    }

    function drawBeam(beam) {
        ctx.save();
        ctx.translate(beam.x, beam.y);
        ctx.rotate((beam.angle * Math.PI) / 180);

        const pulsingOpacity = beam.opacity * (0.8 + Math.sin(beam.pulse) * 0.2);
        const gradient = ctx.createLinearGradient(0, 0, 0, beam.length);

        gradient.addColorStop(0, `hsla(${beam.hue}, 85%, 65%, 0)`);
        gradient.addColorStop(0.1, `hsla(${beam.hue}, 85%, 65%, ${pulsingOpacity * 0.5})`);
        gradient.addColorStop(0.4, `hsla(${beam.hue}, 85%, 65%, ${pulsingOpacity})`);
        gradient.addColorStop(0.6, `hsla(${beam.hue}, 85%, 65%, ${pulsingOpacity})`);
        gradient.addColorStop(0.9, `hsla(${beam.hue}, 85%, 65%, ${pulsingOpacity * 0.5})`);
        gradient.addColorStop(1, `hsla(${beam.hue}, 85%, 65%, 0)`);

        ctx.fillStyle = gradient;
        ctx.fillRect(-beam.width / 2, 0, beam.width, beam.length);
        ctx.restore();
    }

    let animationFrameId = null;
    let isVisible = true;

    function animate() {
        if (!isVisible) {
            animationFrameId = null;
            return;
        }
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        // Costly canvas filter is removed from drawing loop. The blur is offloaded to CSS GPU acceleration.

        beams.forEach((beam, index) => {
            beam.y -= beam.speed;
            beam.pulse += beam.pulseSpeed;

            if (beam.y + beam.length < -100) {
                resetBeam(beam, index);
            }
            drawBeam(beam);
        });

        animationFrameId = requestAnimationFrame(animate);
    }

    // Stop animating when scrolled out of view (e.g. when looking at the hero section)
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            isVisible = entry.isIntersecting;
            if (isVisible && !animationFrameId) {
                animationFrameId = requestAnimationFrame(animate);
            }
        });
    }, { threshold: 0.01 });

    observer.observe(canvas);
}


// ═══════════════════════════════════════════════
//  9. SEED REALISTIC DATA
//     Pre-populates the system with realistic
//     NIET-style data so the dashboard looks
//     impressive during an interview demo.
// ═══════════════════════════════════════════════

const SEED_DATA = {
    admins: [
        { person_id:"A001", admin_id:"ADM001", name:"Dr. Ritu Sharma", email:"ritu.sharma@niet.co.in", contact_number:"9876543001", username:"admin_ritu", password:"admin123", designation:"Placement Coordinator" },
        { person_id:"A002", admin_id:"ADM002", name:"Vikas Mehta", email:"vikas.mehta@niet.co.in", contact_number:"9876543002", username:"admin_vikas", password:"admin123", designation:"Training & Placement Officer" }
    ],
    students: [
        { person_id:"P001", student_id:"S001", name:"Sumit Pathak",       email:"sumit.pathak@niet.co.in",    contact_number:"9876543201", branch:"CSE",          cgpa:"9.2",  skills:"Python, React, Node.js" },
        { person_id:"P002", student_id:"S002", name:"Vanshika Pandey",    email:"vanshika.p@niet.co.in",      contact_number:"9876543202", branch:"CSE",          cgpa:"9.0",  skills:"Java, Spring Boot, SQL" },
        { person_id:"P003", student_id:"S003", name:"Varun Gupta",        email:"varun.gupta@niet.co.in",     contact_number:"9876543203", branch:"CSE (AI & ML)",cgpa:"8.8",  skills:"ML, TensorFlow, Python" },
        { person_id:"P004", student_id:"S004", name:"Aditya Singh",       email:"aditya.singh@niet.co.in",    contact_number:"9876543204", branch:"CSE (DS)",     cgpa:"8.6",  skills:"Data Science, Pandas, R" },
        { person_id:"P005", student_id:"S005", name:"Himanshu Pandey",    email:"himanshu.p@niet.co.in",      contact_number:"9876543205", branch:"CSE (AI)",     cgpa:"8.5",  skills:"AI, NLP, PyTorch" },
        { person_id:"P006", student_id:"S006", name:"Anmol Srivastava",   email:"anmol.s@niet.co.in",         contact_number:"9876543206", branch:"CSE",          cgpa:"8.4",  skills:"Java, DSA, System Design" },
        { person_id:"P007", student_id:"S007", name:"Ayush Mani",         email:"ayush.mani@niet.co.in",      contact_number:"9876543207", branch:"CSE (AI & ML)",cgpa:"8.7",  skills:"ML, Deep Learning, AWS" },
        { person_id:"P008", student_id:"S008", name:"Onkar Jha",          email:"onkar.jha@niet.co.in",       contact_number:"9876543208", branch:"ECE",          cgpa:"8.3",  skills:"Embedded, VLSI, C++" },
        { person_id:"P009", student_id:"S009", name:"Ankush Chauhan",     email:"ankush.c@niet.co.in",        contact_number:"9876543209", branch:"CSE (AI & ML)",cgpa:"8.1",  skills:"Python, Flask, Docker" },
        { person_id:"P010", student_id:"S010", name:"Ayush Rawat",        email:"ayush.rawat@niet.co.in",     contact_number:"9876543210", branch:"CSE (AIML)",   cgpa:"7.9",  skills:"React, MongoDB, Express" },
        { person_id:"P011", student_id:"S011", name:"Priya Sharma",       email:"priya.sharma@niet.co.in",    contact_number:"9876543211", branch:"IT",           cgpa:"8.0",  skills:"Angular, TypeScript, SQL" },
        { person_id:"P012", student_id:"S012", name:"Rohit Verma",        email:"rohit.verma@niet.co.in",     contact_number:"9876543212", branch:"CSE",          cgpa:"7.6",  skills:"C++, Java, Algorithms" },
    ],
    companies: [
        { company_id:"C001", company_name:"Autodesk",      package:"39",    eligibility_cgpa:"8.0", job_role:"Software Engineer" },
        { company_id:"C002", company_name:"AMD",            package:"30",    eligibility_cgpa:"8.0", job_role:"SoC Design Engineer" },
        { company_id:"C003", company_name:"Juspay",         package:"27",    eligibility_cgpa:"7.5", job_role:"Full Stack Developer" },
        { company_id:"C004", company_name:"Atlan",          package:"20",    eligibility_cgpa:"7.5", job_role:"Backend Engineer" },
        { company_id:"C005", company_name:"JP Morgan Chase",package:"19.75", eligibility_cgpa:"7.0", job_role:"Technology Analyst" },
        { company_id:"C006", company_name:"NatWest",        package:"12",    eligibility_cgpa:"7.0", job_role:"Software Developer" },
        { company_id:"C007", company_name:"TCS",            package:"7",     eligibility_cgpa:"6.0", job_role:"Systems Engineer" },
        { company_id:"C008", company_name:"Cognizant",      package:"6",     eligibility_cgpa:"6.0", job_role:"Programmer Analyst" },
    ],
    drives: [
        { drive_id:"D001", company:"C001", drive_date:"2025-09-15" },
        { drive_id:"D002", company:"C002", drive_date:"2025-10-02" },
        { drive_id:"D003", company:"C003", drive_date:"2025-10-20" },
        { drive_id:"D004", company:"C005", drive_date:"2025-11-08" },
        { drive_id:"D005", company:"C007", drive_date:"2025-12-01" },
    ],
    interviews: [
        { interview_id:"I001", student:"S001", company:"C001", interview_date:"2025-09-16" },
        { interview_id:"I002", student:"S003", company:"C001", interview_date:"2025-09-16" },
        { interview_id:"I003", student:"S002", company:"C002", interview_date:"2025-10-03" },
        { interview_id:"I004", student:"S007", company:"C003", interview_date:"2025-10-21" },
        { interview_id:"I005", student:"S006", company:"C005", interview_date:"2025-11-09" },
        { interview_id:"I006", student:"S010", company:"C006", interview_date:"2025-11-10" },
        { interview_id:"I007", student:"S011", company:"C007", interview_date:"2025-12-02" },
        { interview_id:"I008", student:"S009", company:"C003", interview_date:"2025-10-21" },
    ],
    offers: [
        { offer_id:"O001", student:"S001", company:"C001", package:"39" },
        { offer_id:"O002", student:"S003", company:"C001", package:"39" },
        { offer_id:"O003", student:"S002", company:"C002", package:"30" },
        { offer_id:"O004", student:"S007", company:"C003", package:"27" },
        { offer_id:"O005", student:"S006", company:"C005", package:"19.75" },
        { offer_id:"O006", student:"S010", company:"C006", package:"12" },
        { offer_id:"O007", student:"S011", company:"C007", package:"7" },
    ]
};

/**
 * Seed the system with realistic NIET data
 * Only runs if the system currently has 0 students
 */
async function seedDataIfEmpty() {
    const stats = await API.get('/api/stats');
    if (stats.total_students > 0) return; // Already has data

    showToast('Seeding NIET demo data...', 'success');

    // Register admins
    for (const a of SEED_DATA.admins) {
        await API.post('/api/admins', a);
    }
    // Register students
    for (const s of SEED_DATA.students) {
        await API.post('/api/students', s);
    }
    // Register companies
    for (const c of SEED_DATA.companies) {
        await API.post('/api/companies', c);
    }
    // Create drives
    for (const d of SEED_DATA.drives) {
        await API.post('/api/drives', d);
    }
    // Schedule interviews
    for (const i of SEED_DATA.interviews) {
        await API.post('/api/interviews', i);
    }
    // Generate offers
    for (const o of SEED_DATA.offers) {
        await API.post('/api/offers', o);
    }

    showToast('NIET demo data loaded — 12 students, 8 companies, 7 offers!', 'success');
}


// ═══════════════════════════════════════════════
//  10. APP INITIALIZATION
//     Runs when the page loads — sets up
//     everything and loads initial data.
// ═══════════════════════════════════════════════

/** Refresh all data sections */
async function refreshAll() {
    if (currentUserRole === 'admin') {
        await Promise.all([
            renderStats(), renderAdmins(), renderStudents(), renderCompanies(),
            renderDrives(), renderInterviews(), renderOffers(), populateDropdowns()
        ]);
    } else if (currentUserRole === 'student') {
        await Promise.all([
            renderStats(), renderStudents(), renderCompanies(), renderDrives(),
            renderInterviews(), renderOffers(), populateDropdowns()
        ]);
    }
}

// Run when DOM is fully loaded
document.addEventListener('DOMContentLoaded', async () => {
    // Start the WebGL shader background (hero)
    initShaderBackground();

    // Start the Beams background (dashboard)
    initBeamsBackground();

    // Set up sidebar navigation
    setupNavHighlighting();

    const auth = await API.get('/api/auth/me');
    if (auth.authenticated) {
        applyRoleUI(auth.role);
        await refreshAll();
        return;
    }
    selectAuthRole('student');
    selectAuthMode('login');
});
