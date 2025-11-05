const ExcelTemplatesPage = (() => {
    const state = {
        templates: [],
        selectedFile: null,
        isUploading: false,
        tableView: true,
    };

    const elements = {};

    function initElements() {
        elements.dropzone = document.getElementById('dropzone');
        elements.fileInput = document.getElementById('templateFileInput');
        elements.form = document.getElementById('templateForm');
        elements.uploadButton = document.getElementById('uploadBtn');
        elements.uploadSpinner = elements.uploadButton?.querySelector('.spinner-border');
        elements.templateName = document.getElementById('templateName');
        elements.templateCategory = document.getElementById('templateCategory');
        elements.templateDescription = document.getElementById('templateDescription');
        elements.templateVersion = document.getElementById('templateVersion');
        elements.templateRows = document.getElementById('templateRows');
        elements.librarySummary = document.getElementById('librarySummary');
        elements.refreshBtn = document.getElementById('refreshTemplatesBtn');
        elements.cardContainer = document.getElementById('cardView');
        elements.cardToggleBtn = document.getElementById('toggleViewBtnCards');
        elements.tableToggleBtn = document.getElementById('toggleViewBtn');
        elements.tableView = document.getElementById('tableView');
        elements.toastContainer = document.getElementById('toastContainer');
        elements.modal = document.getElementById('templateDetailsModal');
        elements.modalBody = document.getElementById('templateDetailsBody');
    }

    function bindEvents() {
        if (elements.dropzone) {
            ['dragenter', 'dragover'].forEach(evt => {
                elements.dropzone.addEventListener(evt, (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    elements.dropzone.classList.add('dragover');
                });
            });

            ['dragleave', 'drop'].forEach(evt => {
                elements.dropzone.addEventListener(evt, (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    elements.dropzone.classList.remove('dragover');
                });
            });

            elements.dropzone.addEventListener('drop', (event) => {
                const file = event.dataTransfer?.files?.[0];
                if (file) {
                    setSelectedFile(file);
                }
            });
        }

        elements.fileInput?.addEventListener('change', (event) => {
            const file = event.target.files?.[0];
            if (file) {
                setSelectedFile(file);
            }
        });

        elements.form?.addEventListener('submit', handleSubmit);
        elements.refreshBtn?.addEventListener('click', () => loadTemplates(true));
        elements.cardToggleBtn?.addEventListener('click', () => switchView(false));
        elements.tableToggleBtn?.addEventListener('click', () => switchView(true));
    }

    function switchView(showTable) {
        state.tableView = showTable;
        if (showTable) {
            elements.cardContainer?.classList.add('d-none');
            elements.tableView?.classList.remove('d-none');
            elements.tableToggleBtn?.classList.add('active');
            elements.cardToggleBtn?.classList.remove('active');
        } else {
            elements.cardContainer?.classList.remove('d-none');
            elements.tableView?.classList.add('d-none');
            elements.cardToggleBtn?.classList.add('active');
            elements.tableToggleBtn?.classList.remove('active');
        }
    }

    function setSelectedFile(file) {
        if (!file) return;
        const allowedExtensions = ['.xlsx', '.xlsm'];
        const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
        if (!allowedExtensions.includes(extension)) {
            showToast('Only .xlsx or .xlsm files are allowed.', 'danger');
            elements.fileInput.value = '';
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            showToast('File is too large. Maximum size is 10MB.', 'danger');
            elements.fileInput.value = '';
            return;
        }
        state.selectedFile = file;
        elements.templateName.value = elements.templateName.value || file.name.replace(/\.(xlsx|xlsm)$/i, '');
        showToast(`Selected ${file.name}`, 'info');
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (state.isUploading) return;
        if (!state.selectedFile) {
            showToast('Please choose a workbook before uploading.', 'warning');
            elements.fileInput?.focus();
            return;
        }

        const payload = new FormData();
        payload.append('file', state.selectedFile);
        payload.append('name', elements.templateName.value.trim());
        payload.append('category', elements.templateCategory.value.trim());
        payload.append('description', elements.templateDescription.value.trim());

        try {
            setUploading(true);
            const response = await fetch('/api/v1/excel-templates/upload', {
                method: 'POST',
                headers: {
                    ...auth.authHeader(),
                },
                body: payload,
            });

            if (!response.ok) {
                const error = await safeParseJson(response) || {};
                throw new Error(error.detail || 'Upload failed.');
            }

            const data = await response.json();
            showToast(`Template "${data.name}" uploaded successfully.`, 'success');
            resetForm();
            state.templates.unshift(data);
            renderTemplates();
        } catch (error) {
            console.error('Upload error', error);
            showToast(error.message || 'Something went wrong while uploading.', 'danger');
        } finally {
            setUploading(false);
        }
    }

    async function loadTemplates(showToastOnSuccess = false) {
        try {
            setLoadingState(true);
            const response = await fetch('/api/v1/excel-templates/', {
                headers: {
                    'Accept': 'application/json',
                    ...auth.authHeader(),
                },
            });
            if (!response.ok) {
                const error = await safeParseJson(response) || {};
                throw new Error(error.detail || 'Unable to load templates.');
            }

            const data = await response.json();
            state.templates = data.templates || [];
            renderTemplates();
            if (showToastOnSuccess) {
                showToast('Template library refreshed.', 'success');
            }
        } catch (error) {
            console.error('Load templates error', error);
            showToast(error.message || 'Failed to load templates.', 'danger');
            renderTemplatesError(error.message);
        } finally {
            setLoadingState(false);
        }
    }

    function renderTemplatesError(message) {
        if (!elements.templateRows) return;
        elements.templateRows.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4 text-danger">${message}</td>
            </tr>
        `;
        elements.cardContainer.innerHTML = '';
    }

    function renderTemplates() {
        renderTableView();
        renderCardView();
        updateSummary();
    }

    function renderTableView() {
        if (!elements.templateRows) return;
        if (!state.templates.length) {
            elements.templateRows.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-5 text-muted">
                        <div class="empty-state">
                            <i class="bi bi-collection"></i>
                            <h5 class="mt-2 fw-semibold">No templates yet</h5>
                            <p class="mb-0">Upload your first spreadsheet template to get started.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        const rows = state.templates.map(template => {
            const metadata = template.workbook_metadata || {};
            const sheetCount = metadata.sheet_names?.length || 0;
            return `
                <tr data-template-id="${template.id}">
                    <td>
                        <div class="template-name">${escapeHtml(template.name || 'Untitled')}</div>
                        ${template.description ? `<small>${escapeHtml(template.description)}</small>` : ''}
                        ${template.category ? `<span class="badge bg-light text-dark mt-2">${escapeHtml(template.category)}</span>` : ''}
                        ${renderUploaderDetails(template, { variant: 'compact' })}
                    </td>
                    <td>
                        ${sheetCount ? `
                            <span class="badge rounded-pill text-bg-primary">${sheetCount} ${sheetCount === 1 ? 'sheet' : 'sheets'}</span>
                        ` : '<span class="text-muted">—</span>'}
                    </td>
                    <td>${escapeHtml(template.version || '—')}</td>
                    <td>${formatDate(template.updated_at)}</td>
                    <td class="text-end">
                        <div class="btn-group btn-group-sm" role="group">
                            <a class="btn btn-outline-primary" href="${template.download_url}" target="_blank" rel="noopener">
                                <i class="bi bi-download"></i>
                            </a>
                            <button class="btn btn-outline-secondary" data-action="details" data-id="${template.id}">
                                <i class="bi bi-info-circle"></i>
                            </button>
                            <button class="btn btn-outline-danger" data-action="delete" data-id="${template.id}">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        elements.templateRows.innerHTML = rows;
        elements.templateRows.querySelectorAll('button[data-action="delete"]').forEach(button => {
            button.addEventListener('click', () => handleDelete(button.dataset.id));
        });
        elements.templateRows.querySelectorAll('button[data-action="details"]').forEach(button => {
            button.addEventListener('click', () => showDetails(button.dataset.id));
        });
    }

    function renderCardView() {
        if (!elements.cardContainer) return;
        if (!state.templates.length) {
            elements.cardContainer.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-collection"></i>
                    <h5 class="mt-2 fw-semibold">No templates yet</h5>
                    <p class="mb-0">Upload your first spreadsheet template to get started.</p>
                </div>
            `;
            return;
        }

        const cards = state.templates.map(template => {
            const metadata = template.workbook_metadata || {};
            const sheetTags = (metadata.sheet_names || []).map(name => `<li>${escapeHtml(name)}</li>`).join('');
            const namedRanges = (metadata.named_ranges || []).slice(0, 6).map(name => `<li>${escapeHtml(name)}</li>`).join('');
            return `
                <div class="border rounded-3 p-4 mb-3" data-template-id="${template.id}">
                    <div class="d-flex justify-content-between flex-wrap gap-3 mb-3">
                        <div>
                            <h5 class="mb-1">${escapeHtml(template.name || 'Untitled')}</h5>
                            ${template.description ? `<p class="text-muted mb-0">${escapeHtml(template.description)}</p>` : ''}
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <a class="btn btn-outline-primary btn-sm" href="${template.download_url}" target="_blank" rel="noopener">
                                <i class="bi bi-download me-1"></i> Download
                            </a>
                            <button class="btn btn-outline-secondary btn-sm" data-action="details" data-id="${template.id}">
                                <i class="bi bi-info-circle me-1"></i> Details
                            </button>
                            <button class="btn btn-outline-danger btn-sm" data-action="delete" data-id="${template.id}">
                                <i class="bi bi-trash me-1"></i> Delete
                            </button>
                        </div>
                    </div>
                    <div class="metadata-grid">
                        <div class="metadata-item">
                            <h6>Category</h6>
                            <span>${escapeHtml(template.category || '—')}</span>
                        </div>
                        <div class="metadata-item">
                            <h6>Version</h6>
                            <span>${escapeHtml(template.version || '—')}</span>
                        </div>
                        <div class="metadata-item">
                            <h6>Updated</h6>
                            <span>${formatDate(template.updated_at)}</span>
                        </div>
                        <div class="metadata-item">
                            <h6>Uploaded</h6>
                            <span>${formatDate(template.created_at)}</span>
                        </div>
                        <div class="metadata-item">
                            <h6>Sheets</h6>
                            <span>${(metadata.sheet_names || []).length || '—'}</span>
                        </div>
                    </div>
                    ${renderUploaderDetails(template, { variant: 'card' })}
                    ${sheetTags ? `
                        <div class="mt-3">
                            <span class="fw-semibold text-muted d-block mb-2">Sheets</span>
                            <ul class="metadata-list">${sheetTags}</ul>
                        </div>
                    ` : ''}
                    ${namedRanges ? `
                        <div class="mt-3">
                            <span class="fw-semibold text-muted d-block mb-2">Named ranges</span>
                            <ul class="metadata-list">${namedRanges}</ul>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

        elements.cardContainer.innerHTML = cards;
        elements.cardContainer.querySelectorAll('button[data-action="delete"]').forEach(button => {
            button.addEventListener('click', () => handleDelete(button.dataset.id));
        });
        elements.cardContainer.querySelectorAll('button[data-action="details"]').forEach(button => {
            button.addEventListener('click', () => showDetails(button.dataset.id));
        });
    }

    function updateSummary() {
        if (!elements.librarySummary) return;
        if (!state.templates.length) {
            elements.librarySummary.textContent = 'No templates uploaded yet.';
            return;
        }
        const sheetCount = state.templates.reduce((total, template) => total + (template.workbook_metadata?.sheet_names?.length || 0), 0);
        elements.librarySummary.textContent = `${state.templates.length} template${state.templates.length === 1 ? '' : 's'} • ${sheetCount} total sheet${sheetCount === 1 ? '' : 's'}`;
    }

    function resolveUploader(template) {
        return template?.uploaded_by_user || null;
    }

    function getUploaderDisplayName(uploader) {
        if (!uploader) return '';
        if (uploader.display_name) return uploader.display_name;
        const nameParts = [uploader.first_name, uploader.last_name].filter(Boolean).join(' ').trim();
        if (nameParts) return nameParts;
        if (uploader.username) return uploader.username;
        if (uploader.email) return uploader.email;
        return '';
    }

    function renderAvatarElement(uploader, size = 'avatar-sm') {
        if (!uploader) return '';
        const displayName = getUploaderDisplayName(uploader) || 'User';
        const alt = escapeHtml(displayName);
        if (uploader.avatar_url) {
            const url = escapeHtml(uploader.avatar_url);
            return `<span class="avatar-circle ${size}"><img src="${url}" alt="${alt}"></span>`;
        }
        const initialsSource = (uploader.initials || displayName || '?').trim().slice(0, 2) || '?';
        const initials = escapeHtml(initialsSource.toUpperCase());
        const background = escapeHtml(uploader.avatar_background || 'var(--primary)');
        return `<span class="avatar-circle ${size}" style="background:${background}">${initials}</span>`;
    }

    function renderUploaderDetails(template, options = {}) {
        const uploader = resolveUploader(template);
        if (!uploader) return '';

        const variant = options.variant || 'compact';
        const normalizedVariant = ['card', 'detailed', 'modal'].includes(variant) ? 'detailed' : 'compact';
        const includeDate = options.includeDate !== false;

        const displayName = getUploaderDisplayName(uploader) || 'Unknown user';
        const uploadedDate = includeDate && template?.created_at ? formatDate(template.created_at) : null;

        const badges = [];
        if (uploader.role) {
            badges.push(`<span class="badge bg-light border text-muted">${escapeHtml(uploader.role)}</span>`);
        }
        const branchTokens = [];
        if (uploader.branch_name) {
            branchTokens.push(uploader.branch_name);
        }
        if (uploader.branch_code) {
            branchTokens.push(`(${uploader.branch_code})`);
        }
        const branchLabel = branchTokens.length ? branchTokens.join(' ') : '';

        const badgeWrap = badges.length ? `<div class="d-flex flex-wrap gap-1">${badges.join('')}</div>` : '';
        const emailLine = uploader.email ? `<div class="text-muted xsmall">${escapeHtml(uploader.email)}</div>` : '';
        const dateLine = uploadedDate ? `<div class="text-muted xsmall">Uploaded ${uploadedDate}</div>` : '';
        const branchLine = branchLabel
            ? `<div class="text-muted xsmall">Branch: ${escapeHtml(branchLabel)}</div>`
            : '';

        const sizeClass = normalizedVariant === 'compact' ? 'avatar-sm' : 'avatar-md';
        const marginClass = normalizedVariant === 'compact' ? 'mt-2' : 'mt-3';
        const alignment = normalizedVariant === 'compact' ? 'align-items-center' : 'align-items-start';
        const nameClass = normalizedVariant === 'compact' ? ' small' : '';

        return `
            <div class="d-flex ${alignment} gap-3 ${marginClass} uploader-meta">
                ${renderAvatarElement(uploader, sizeClass)}
                <div class="d-flex flex-column gap-1">
                    <div class="fw-semibold${nameClass}">${escapeHtml(displayName)}</div>
                    ${badgeWrap}
                    ${branchLine}
                    ${emailLine}
                    ${dateLine}
                </div>
            </div>
        `;
    }

    async function handleDelete(id) {
        const template = state.templates.find(item => item.id === id);
        if (!template) return;

        const confirmed = confirm(`Delete template "${template.name}"? This will remove the stored workbook.`);
        if (!confirmed) return;

        try {
            const response = await fetch(`/api/v1/excel-templates/${id}`, {
                method: 'DELETE',
                headers: {
                    ...auth.authHeader(),
                },
            });
            if (!response.ok) {
                const error = await safeParseJson(response) || {};
                throw new Error(error.detail || 'Failed to delete template.');
            }
            state.templates = state.templates.filter(item => item.id !== id);
            renderTemplates();
            showToast('Template removed.', 'success');
        } catch (error) {
            console.error('Delete template error', error);
            showToast(error.message || 'Could not delete template.', 'danger');
        }
    }

    function showDetails(id) {
        const template = state.templates.find(item => item.id === id);
        if (!template || !elements.modal) return;
        const metadata = template.workbook_metadata || {};
        const size = template.file_size ? `${(template.file_size / 1024).toFixed(1)} KB` : 'Unknown';
        const sheets = metadata.sheet_names?.map(name => `<li>${escapeHtml(name)}</li>`).join('') || '<li><em>No sheets detected</em></li>';
        const namedRanges = (metadata.named_ranges?.length ? metadata.named_ranges.map(name => `<li>${escapeHtml(name)}</li>`).join('') : '<li><em>None</em></li>');

        const docProps = metadata.document_properties || {};
        const docPropsHtml = Object.keys(docProps).length
            ? Object.entries(docProps).map(([key, value]) => `<div class="metadata-item"><h6>${escapeHtml(key)}</h6><span>${escapeHtml(String(value))}</span></div>`).join('')
            : '<p class="text-muted mb-0">No document properties available.</p>';

        elements.modalBody.innerHTML = `
            <div class="mb-3">
                <h4 class="fw-semibold mb-1">${escapeHtml(template.name || 'Untitled')}</h4>
                ${template.description ? `<p class="text-muted mb-2">${escapeHtml(template.description)}</p>` : ''}
                <div class="d-flex flex-wrap gap-2">
                    <span class="badge bg-primary-subtle text-primary"><i class="bi bi-folder me-1"></i>${escapeHtml(template.category || 'Uncategorised')}</span>
                    <span class="badge bg-secondary-subtle text-secondary"><i class="bi bi-hash me-1"></i>${escapeHtml(template.version || '—')}</span>
                    <span class="badge bg-success-subtle text-success"><i class="bi bi-hdd-stack me-1"></i>${size}</span>
                </div>
                ${renderUploaderDetails(template, { variant: 'detailed' })}
            </div>
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="border rounded-3 p-3">
                        <h6 class="fw-semibold mb-2">Sheets</h6>
                        <ul class="metadata-list flex-column">${sheets}</ul>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="border rounded-3 p-3">
                        <h6 class="fw-semibold mb-2">Named ranges</h6>
                        <ul class="metadata-list flex-column">${namedRanges}</ul>
                    </div>
                </div>
            </div>
            <div class="border rounded-3 p-3 mt-3">
                <h6 class="fw-semibold mb-2">Document properties</h6>
                <div class="metadata-grid">${docPropsHtml}</div>
            </div>
        `;

        const modalInstance = bootstrap.Modal.getOrCreateInstance(elements.modal);
        modalInstance.show();
    }

    function resetForm() {
        elements.form?.reset();
        elements.fileInput.value = '';
        elements.templateVersion.value = '';
        state.selectedFile = null;
    }

    function setUploading(isUploading) {
        state.isUploading = isUploading;
        if (isUploading) {
            elements.uploadButton?.setAttribute('disabled', 'disabled');
            elements.uploadSpinner?.classList.remove('d-none');
        } else {
            elements.uploadButton?.removeAttribute('disabled');
            elements.uploadSpinner?.classList.add('d-none');
        }
    }

    function setLoadingState(isLoading) {
        if (!elements.refreshBtn) return;
        elements.refreshBtn.disabled = isLoading;
        elements.refreshBtn.innerHTML = isLoading
            ? '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Refreshing'
            : '<i class="bi bi-arrow-clockwise"></i> Refresh';
    }

    function showToast(message, variant = 'primary', timeout = 3600) {
        if (!elements.toastContainer) return alert(message);
        const toast = document.createElement('div');
        toast.className = `toast align-items-center border-0 text-bg-${variant}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${escapeHtml(message)}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        elements.toastContainer.appendChild(toast);
        const toastInstance = new bootstrap.Toast(toast, { delay: timeout });
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
        toastInstance.show();
    }

    function formatDate(value) {
        if (!value) return '—';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '—';
        return date.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    }

    async function safeParseJson(response) {
        try {
            return await response.json();
        } catch (error) {
            return null;
        }
    }

    function escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function bootstrapPage() {
        if (!auth.requireAuth()) return;
        initElements();
        bindEvents();
        switchView(true);
        loadTemplates();
    }

    return {
        init() {
            document.addEventListener('DOMContentLoaded', () => {
                initializeNavbar('excel-templates');
                bootstrapPage();
            });
        },
    };
})();

ExcelTemplatesPage.init();
