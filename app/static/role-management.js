// Global variables
let roles = [];
let permissions = [];
let privilegeChart = {};
let auditLogs = [];

// Initialize page
document.addEventListener('DOMContentLoaded', function () {
    loadStatistics();
    loadRoles();
    loadPermissions();
    loadPrivilegeChart();
    loadAuditLog();
});

// Load statistics
async function loadStatistics() {
    try {
        const [rolesResponse, permissionsResponse, auditResponse] = await Promise.all([
            fetch('/api/v1/roles/', { headers: auth.authHeader() }),
            fetch('/api/v1/roles/permissions', { headers: auth.authHeader() }),
            fetch('/api/v1/roles/audit-logs/', { headers: auth.authHeader() })
        ]);

        if (rolesResponse.ok) {
            const rolesData = await rolesResponse.json();
            document.getElementById('total-roles').textContent = rolesData.length;
        }

        if (permissionsResponse.ok) {
            const permissionsData = await permissionsResponse.json();
            document.getElementById('total-permissions').textContent = permissionsData.length;
        }

        if (auditResponse.ok) {
            const auditData = await auditResponse.json();
            document.getElementById('audit-entries').textContent = auditData.length;
        }

        // Get total users (this would need a separate endpoint)
        document.getElementById('total-users').textContent = '-';
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load roles
async function loadRoles() {
    try {
        const response = await fetch('/api/v1/roles/', { headers: auth.authHeader() });
        if (response.ok) {
            roles = await response.json();
            displayRoles();
        } else {
            console.error('Failed to load roles');
        }
    } catch (error) {
        console.error('Error loading roles:', error);
    }
}

// Display roles
function displayRoles() {
    const container = document.getElementById('roles-container');
    container.innerHTML = '';

    roles.forEach(role => {
        const roleCard = document.createElement('div');
        roleCard.className = `role-card ${role.is_system_role ? 'system-role' : 'custom-role'}`;

        roleCard.innerHTML = `
            <div class="role-header">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h5 class="mb-0">${role.name}</h5>
                        <small class="text-muted">${role.description || 'No description'}</small>
                    </div>
                    <div>
                        ${role.is_system_role ? '<span class="badge bg-primary">System</span>' : ''}
                        <button class="btn btn-sm btn-outline-primary ms-2" onclick="editRole('${role.id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        ${!role.is_system_role ? `
                            <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteRole('${role.id}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
            <div class="role-body">
                <div class="row">
                    <div class="col-md-6">
                        <strong>Created:</strong> ${new Date(role.created_at).toLocaleDateString()}
                    </div>
                    <div class="col-md-6">
                        <strong>Status:</strong>
                        <span class="badge ${role.is_active ? 'bg-success' : 'bg-danger'}">
                            ${role.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </div>
            </div>
        `;

        container.appendChild(roleCard);
    });
}

// Load permissions
async function loadPermissions() {
    try {
        const response = await fetch('/api/v1/roles/permissions', { headers: auth.authHeader() });
        if (response.ok) {
            permissions = await response.json();
            displayPermissions();
        } else {
            console.error('Failed to load permissions');
        }
    } catch (error) {
        console.error('Error loading permissions:', error);
    }
}

// Display permissions
function displayPermissions() {
    const container = document.getElementById('permissions-container');
    container.innerHTML = '';

    // Group permissions by module
    const moduleGroups = {};
    permissions.forEach(permission => {
        if (!moduleGroups[permission.module]) {
            moduleGroups[permission.module] = [];
        }
        moduleGroups[permission.module].push(permission);
    });

    Object.keys(moduleGroups).forEach(module => {
        const moduleSection = document.createElement('div');
        moduleSection.className = 'module-section';

        moduleSection.innerHTML = `
            <div class="module-header" onclick="toggleModule('${module}')">
                <i class="fas fa-chevron-down"></i> ${module.charAt(0).toUpperCase() + module.slice(1)}
                <span class="badge bg-secondary ms-2">${moduleGroups[module].length}</span>
            </div>
            <div class="permissions-grid" id="module-${module}">
                ${moduleGroups[module].map(permission => `
                    <div class="permission-item">
                        <i class="fas fa-key"></i>
                        <div>
                            <strong>${permission.name}</strong><br>
                            <small class="text-muted">${permission.action} ${permission.resource}</small>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        container.appendChild(moduleSection);
    });
}

// Toggle module visibility
function toggleModule(module) {
    const moduleContent = document.getElementById(`module-${module}`);
    const header = moduleContent.previousElementSibling;
    const icon = header.querySelector('i');

    if (moduleContent.style.display === 'none') {
        moduleContent.style.display = 'grid';
        icon.className = 'fas fa-chevron-down';
    } else {
        moduleContent.style.display = 'none';
        icon.className = 'fas fa-chevron-right';
    }
}

// Load privilege chart
async function loadPrivilegeChart() {
    try {
        const response = await fetch('/api/v1/roles/privilege-chart', { headers: auth.authHeader() });
        if (response.ok) {
            privilegeChart = await response.json();
            displayPrivilegeChart();
        } else {
            console.error('Failed to load privilege chart');
        }
    } catch (error) {
        console.error('Error loading privilege chart:', error);
    }
}

// Display privilege chart
function displayPrivilegeChart() {
    const container = document.getElementById('privilege-chart-container');
    container.innerHTML = '';

    if (!privilegeChart.modules || !privilegeChart.roles) {
        container.innerHTML = '<div class="alert alert-info">No privilege chart data available</div>';
        return;
    }

    const chartDiv = document.createElement('div');
    chartDiv.className = 'privilege-chart';

    let chartHTML = `
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Module/Permission</th>
                        ${privilegeChart.roles.map(role => `<th>${role.name}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
    `;

    privilegeChart.modules.forEach(module => {
        chartHTML += `
            <tr class="table-primary">
                <td colspan="${privilegeChart.roles.length + 1}">
                    <strong>${module.name}</strong>
                </td>
            </tr>
        `;

        module.permissions.forEach(permission => {
            chartHTML += '<tr>';
            chartHTML += `<td>${permission.name}</td>`;

            privilegeChart.roles.forEach(role => {
                const hasPermission = role.permissions.some(p =>
                    p.permission_id === permission.id
                );
                chartHTML += `
                    <td class="text-center">
                        <input type="checkbox"
                               class="form-check-input"
                               ${hasPermission ? 'checked' : ''}
                               onchange="updatePrivilegeAssignment('${role.id}', '${permission.id}', this.checked)">
                    </td>
                `;
            });

            chartHTML += '</tr>';
        });
    });

    chartHTML += `
                </tbody>
            </table>
        </div>
    `;

    chartDiv.innerHTML = chartHTML;
    container.appendChild(chartDiv);
}

// Update privilege assignment
function updatePrivilegeAssignment(roleId, permissionId, hasPermission) {
    if (!privilegeChart.assignments) {
        privilegeChart.assignments = [];
    }

    const existingIndex = privilegeChart.assignments.findIndex(
        a => a.role_id === roleId && a.permission_id === permissionId
    );

    if (hasPermission && existingIndex === -1) {
        privilegeChart.assignments.push({
            role_id: roleId,
            permission_id: permissionId
        });
    } else if (!hasPermission && existingIndex !== -1) {
        privilegeChart.assignments.splice(existingIndex, 1);
    }
}

// Save privilege assignments
async function savePrivilegeAssignments() {
    try {
        const response = await fetch('/api/v1/roles/assign-privileges', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...auth.authHeader()
            },
            body: JSON.stringify({
                assignments: privilegeChart.assignments || []
            })
        });

        if (response.ok) {
            showNotification('Privilege assignments saved successfully!', 'success');
            loadPrivilegeChart(); // Refresh the chart
        } else {
            const error = await response.json();
            showNotification(`Failed to save assignments: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error saving privilege assignments:', error);
        showNotification('Error saving privilege assignments', 'error');
    }
}

// Load audit log
async function loadAuditLog() {
    try {
        const filter = document.getElementById('audit-filter').value;
        const url = filter ? `/api/v1/roles/audit-logs/?action=${filter}` : '/api/v1/roles/audit-logs/';

        const response = await fetch(url, { headers: auth.authHeader() });
        if (response.ok) {
            auditLogs = await response.json();
            displayAuditLog();
        } else {
            console.error('Failed to load audit log');
        }
    } catch (error) {
        console.error('Error loading audit log:', error);
    }
}

// Display audit log
function displayAuditLog() {
    const container = document.getElementById('audit-container');
    container.innerHTML = '';

    if (auditLogs.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No audit entries found</div>';
        return;
    }

    auditLogs.forEach(entry => {
        const entryDiv = document.createElement('div');
        entryDiv.className = `audit-entry ${entry.action}`;

        entryDiv.innerHTML = `
            <div class="d-flex justify-content-between">
                <div>
                    <strong>${entry.action.toUpperCase()}</strong> - ${entry.module}
                    ${entry.resource_type ? `(${entry.resource_type})` : ''}
                </div>
                <small class="text-muted">${new Date(entry.created_at).toLocaleString()}</small>
            </div>
            <div class="mt-2">
                <strong>User:</strong> ${entry.user?.username || 'Unknown'}
                ${entry.details ? `<br><strong>Details:</strong> ${JSON.stringify(entry.details)}` : ''}
            </div>
        `;

        container.appendChild(entryDiv);
    });
}

// Refresh audit log
function refreshAuditLog() {
    loadAuditLog();
}

// Modal functions
function showCreateRoleModal() {
    document.getElementById('createRoleForm').reset();
    new bootstrap.Modal(document.getElementById('createRoleModal')).show();
}

function showCreatePermissionModal() {
    document.getElementById('createPermissionForm').reset();
    new bootstrap.Modal(document.getElementById('createPermissionModal')).show();
}

function showEditRoleModal(roleId) {
    const role = roles.find(r => r.id === roleId);
    if (role) {
        document.getElementById('editRoleId').value = role.id;
        document.getElementById('editRoleName').value = role.name;
        document.getElementById('editRoleDescription').value = role.description || '';
        new bootstrap.Modal(document.getElementById('editRoleModal')).show();
    }
}

// Create role
async function createRole() {
    const formData = {
        name: document.getElementById('roleName').value,
        description: document.getElementById('roleDescription').value,
        is_system_role: document.getElementById('isSystemRole').checked
    };

    try {
        const response = await fetch('/api/v1/roles/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...auth.authHeader()
            },
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            showNotification('Role created successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createRoleModal')).hide();
            loadRoles();
            loadStatistics();
        } else {
            const error = await response.json();
            showNotification(`Failed to create role: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error creating role:', error);
        showNotification('Error creating role', 'error');
    }
}

// Create permission
async function createPermission() {
    const formData = {
        name: document.getElementById('permissionName').value,
        description: document.getElementById('permissionDescription').value,
        module: document.getElementById('permissionModule').value,
        action: document.getElementById('permissionAction').value,
        resource: document.getElementById('permissionResource').value
    };

    try {
        const response = await fetch('/api/v1/roles/permissions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...auth.authHeader()
            },
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            showNotification('Permission created successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createPermissionModal')).hide();
            loadPermissions();
            loadStatistics();
        } else {
            const error = await response.json();
            showNotification(`Failed to create permission: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error creating permission:', error);
        showNotification('Error creating permission', 'error');
    }
}

// Edit role
function editRole(roleId) {
    showEditRoleModal(roleId);
}

// Update role
async function updateRole() {
    const roleId = document.getElementById('editRoleId').value;
    const formData = {
        name: document.getElementById('editRoleName').value,
        description: document.getElementById('editRoleDescription').value
    };

    try {
        const response = await fetch(`/api/v1/roles/${roleId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...auth.authHeader()
            },
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            showNotification('Role updated successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('editRoleModal')).hide();
            loadRoles();
        } else {
            const error = await response.json();
            showNotification(`Failed to update role: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error updating role:', error);
        showNotification('Error updating role', 'error');
    }
}

// Delete role
async function deleteRole(roleId) {
    if (!confirm('Are you sure you want to delete this role? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/roles/${roleId}`, {
            method: 'DELETE',
            headers: auth.authHeader()
        });

        if (response.ok) {
            showNotification('Role deleted successfully!', 'success');
            loadRoles();
            loadStatistics();
        } else {
            const error = await response.json();
            showNotification(`Failed to delete role: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting role:', error);
        showNotification('Error deleting role', 'error');
    }
}

// Notification function
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Event listeners
document.addEventListener('DOMContentLoaded', function () {
    const auditFilter = document.getElementById('audit-filter');
    if (auditFilter) {
        auditFilter.addEventListener('change', loadAuditLog);
    }
});
