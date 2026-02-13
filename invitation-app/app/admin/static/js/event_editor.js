// Live Preview
const fields = ['title', 'host', 'date', 'time', 'location', 'message'];
const templateRadios = document.querySelectorAll('input[name="template"]');
let currentTemplate = '';

function updatePreview() {
    const selected = document.querySelector('input[name="template"]:checked');
    if (!selected) return;

    const templateName = selected.value;

    // Fetch template HTML
    fetch('/api/template-preview/' + templateName)
        .then(r => r.text())
        .then(html => {
            // Replace placeholders with form values
            const replacements = {
                '{{title}}': document.getElementById('title').value || 'Event Title',
                '{{host}}': document.getElementById('host').value || 'Host Name',
                '{{date}}': formatDate(document.getElementById('date').value) || 'Date TBD',
                '{{time}}': formatTime(document.getElementById('time').value) || 'Time TBD',
                '{{location}}': document.getElementById('location').value || 'Location TBD',
                '{{message}}': document.getElementById('message').value || 'You\'re invited to celebrate with us!',
                '{{guest_name}}': 'Guest Name',
                '{{rsvp_url}}': '#',
                '{{photo_display}}': 'none',
            };

            for (const [key, value] of Object.entries(replacements)) {
                html = html.split(key).join(value);
            }

            const frame = document.getElementById('previewFrame');
            frame.innerHTML = '';
            const iframe = document.createElement('iframe');
            iframe.style.width = '100%';
            iframe.style.minHeight = '500px';
            iframe.style.border = 'none';
            frame.appendChild(iframe);
            iframe.contentDocument.open();
            iframe.contentDocument.write(html);
            iframe.contentDocument.close();

            // Auto-resize iframe
            setTimeout(() => {
                const h = iframe.contentDocument.body.scrollHeight;
                iframe.style.height = h + 20 + 'px';
            }, 100);
        });
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

function formatTime(timeStr) {
    if (!timeStr) return '';
    const [h, m] = timeStr.split(':');
    const hour = parseInt(h);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const h12 = hour % 12 || 12;
    return h12 + ':' + m + ' ' + ampm;
}

// Attach listeners
fields.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', updatePreview);
});
templateRadios.forEach(r => r.addEventListener('change', updatePreview));

// Initial preview
updatePreview();

// Contact search & selection
const contactSearch = document.getElementById('contactSearch');
if (contactSearch) {
    contactSearch.addEventListener('input', function () {
        const q = this.value.toLowerCase();
        document.querySelectorAll('.contact-checkbox').forEach(el => {
            const text = el.textContent.toLowerCase();
            el.style.display = text.includes(q) ? 'flex' : 'none';
        });
    });
}

function selectByTag(tag) {
    document.querySelectorAll('.contact-checkbox').forEach(el => {
        const tags = (el.getAttribute('data-tags') || '').split(',');
        if (tags.includes(tag)) {
            const cb = el.querySelector('input[type="checkbox"]');
            cb.checked = true;
            var select = el.querySelector('.send-method-select');
            if (select) select.style.display = 'inline-block';
        }
    });
    updateSelectedCount();
}

function selectAll(checked) {
    document.querySelectorAll('.contact-checkbox input[type="checkbox"]').forEach(cb => {
        if (cb.closest('.contact-checkbox').style.display !== 'none') {
            cb.checked = checked;
        }
    });
    updateSelectedCount();
}

function updateSelectedCount() {
    const count = document.querySelectorAll('.contact-checkbox input:checked').length;
    const el = document.getElementById('selectedCount');
    if (el) el.textContent = count + ' selected';
}

document.querySelectorAll('.contact-checkbox input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', function () {
        updateSelectedCount();
        // Show/hide the send method dropdown
        const select = this.closest('.contact-checkbox').querySelector('.send-method-select');
        if (select) {
            select.style.display = this.checked ? 'inline-block' : 'none';
        }
    });
});

// Hide all send method dropdowns initially
document.querySelectorAll('.send-method-select').forEach(sel => {
    sel.style.display = 'none';
});
