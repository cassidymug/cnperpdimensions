// Modern JavaScript Framework for CNPERP ERP System

class ModernUI {
    constructor() {
        this.init();
    }

    init() {
        this.setupThemeToggle();
        this.setupAnimations();
        this.setupMicroInteractions();
        this.setupFormEnhancements();
        this.setupTableEnhancements();
        this.setupModalEnhancements();
        this.setupLoadingStates();
        this.setupNotifications();
        this.setupKeyboardShortcuts();
    }

    // Theme Toggle with Smooth Transitions
    setupThemeToggle() {
        const themeToggle = document.querySelector('.theme-toggle');
        const html = document.documentElement;
        
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const isDark = html.getAttribute('data-theme') === 'dark';
                html.setAttribute('data-theme', isDark ? 'light' : 'dark');
                themeToggle.classList.toggle('active');
                
                // Add transition class for smooth color changes
                html.classList.add('theme-transition');
                setTimeout(() => html.classList.remove('theme-transition'), 300);
                
                // Save preference
                localStorage.setItem('theme', html.getAttribute('data-theme'));
            });
        }

        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        html.setAttribute('data-theme', savedTheme);
        if (themeToggle && savedTheme === 'dark') {
            themeToggle.classList.add('active');
        }
    }

    // Smooth Animations and Transitions
    setupAnimations() {
        // Intersection Observer for scroll animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in-up');
                }
            });
        }, observerOptions);

        // Observe all cards and sections
        document.querySelectorAll('.modern-card, .glass-card, .neu-card').forEach(el => {
            observer.observe(el);
        });

        // Parallax effect for hero sections
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const parallaxElements = document.querySelectorAll('.parallax');
            
            parallaxElements.forEach(element => {
                const speed = element.dataset.speed || 0.5;
                element.style.transform = `translateY(${scrolled * speed}px)`;
            });
        });
    }

    // Micro-interactions for Enhanced UX
    setupMicroInteractions() {
        // Button hover effects
        document.querySelectorAll('.btn-modern').forEach(btn => {
            btn.addEventListener('mouseenter', (e) => {
                this.createRippleEffect(e);
            });
        });

        // Card hover effects
        document.querySelectorAll('.modern-card, .glass-card, .neu-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-8px) scale(1.02)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0) scale(1)';
            });
        });

        // Form input focus effects
        document.querySelectorAll('.form-control-modern').forEach(input => {
            input.addEventListener('focus', () => {
                input.parentElement.classList.add('focused');
            });

            input.addEventListener('blur', () => {
                input.parentElement.classList.remove('focused');
            });
        });
    }

    // Enhanced Form Interactions
    setupFormEnhancements() {
        // Auto-resize textareas
        document.querySelectorAll('textarea').forEach(textarea => {
            textarea.addEventListener('input', () => {
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            });
        });

        // Real-time form validation
        document.querySelectorAll('.form-control-modern').forEach(input => {
            input.addEventListener('input', () => {
                this.validateField(input);
            });

            input.addEventListener('blur', () => {
                this.validateField(input);
            });
        });

        // Auto-save functionality
        let autoSaveTimeout;
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('input', () => {
                clearTimeout(autoSaveTimeout);
                autoSaveTimeout = setTimeout(() => {
                    this.autoSaveForm(form);
                }, 2000);
            });
        });
    }

    // Enhanced Table Interactions
    setupTableEnhancements() {
        // Sortable tables
        document.querySelectorAll('.table-modern th[data-sort]').forEach(header => {
            header.addEventListener('click', () => {
                this.sortTable(header);
            });
        });

        // Row selection
        document.querySelectorAll('.table-modern tbody tr').forEach(row => {
            row.addEventListener('click', () => {
                row.classList.toggle('selected');
            });
        });

        // Bulk actions
        const selectAllCheckbox = document.querySelector('#selectAll');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', () => {
                const checkboxes = document.querySelectorAll('.table-modern tbody input[type="checkbox"]');
                checkboxes.forEach(checkbox => {
                    checkbox.checked = selectAllCheckbox.checked;
                });
                this.updateBulkActions();
            });
        }
    }

    // Enhanced Modal Interactions
    setupModalEnhancements() {
        // Smooth modal animations
        document.querySelectorAll('[data-bs-toggle="modal"]').forEach(trigger => {
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                const target = trigger.getAttribute('data-bs-target');
                this.openModal(target);
            });
        });

        // Modal backdrop click to close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-backdrop')) {
                this.closeModal();
            }
        });

        // ESC key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    // Loading States and Progress Indicators
    setupLoadingStates() {
        // Show loading state for async operations
        this.showLoading = (element) => {
            element.classList.add('loading');
            element.innerHTML = '<div class="loading-modern"></div>';
        };

        this.hideLoading = (element, originalContent) => {
            element.classList.remove('loading');
            element.innerHTML = originalContent;
        };

        // Progress bar animations
        document.querySelectorAll('.progress-bar-modern').forEach(bar => {
            const width = bar.style.width;
            bar.style.width = '0%';
            
            setTimeout(() => {
                bar.style.width = width;
            }, 100);
        });
    }

    // Modern Notification System
    setupNotifications() {
        this.showNotification = (message, type = 'info', duration = 5000) => {
            const notification = document.createElement('div');
            notification.className = `alert-modern alert-${type} notification-modern`;
            notification.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="bi bi-${this.getNotificationIcon(type)} me-2"></i>
                    <span>${message}</span>
                    <button class="btn-close ms-auto" onclick="this.parentElement.parentElement.remove()"></button>
                </div>
            `;

            document.body.appendChild(notification);

            // Animate in
            notification.style.opacity = '0';
            notification.style.transform = 'translateY(-20px)';
            
            setTimeout(() => {
                notification.style.opacity = '1';
                notification.style.transform = 'translateY(0)';
            }, 100);

            // Auto remove
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateY(-20px)';
                setTimeout(() => notification.remove(), 300);
            }, duration);
        };

        this.getNotificationIcon = (type) => {
            const icons = {
                success: 'check-circle',
                warning: 'exclamation-triangle',
                danger: 'x-circle',
                info: 'info-circle'
            };
            return icons[type] || 'info-circle';
        };
    }

    // Keyboard Shortcuts
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + S to save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.saveCurrentForm();
            }

            // Ctrl/Cmd + N for new item
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                this.createNewItem();
            }

            // Ctrl/Cmd + F for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                this.focusSearch();
            }

            // Ctrl/Cmd + E for export
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
                e.preventDefault();
                this.exportData();
            }
        });
    }

    // Utility Methods
    createRippleEffect(event) {
        const button = event.currentTarget;
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');

        button.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
    }

    validateField(input) {
        const value = input.value.trim();
        const fieldName = input.name;
        let isValid = true;
        let errorMessage = '';

        // Basic validation rules
        if (input.required && !value) {
            isValid = false;
            errorMessage = 'This field is required';
        } else if (input.type === 'email' && value && !this.isValidEmail(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid email address';
        } else if (input.type === 'tel' && value && !this.isValidPhone(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid phone number';
        }

        this.showFieldValidation(input, isValid, errorMessage);
    }

    showFieldValidation(input, isValid, message) {
        const container = input.parentElement;
        const existingError = container.querySelector('.field-error');

        if (existingError) {
            existingError.remove();
        }

        input.classList.toggle('is-invalid', !isValid);
        input.classList.toggle('is-valid', isValid && input.value.trim());

        if (!isValid && message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error text-danger mt-1';
            errorDiv.textContent = message;
            container.appendChild(errorDiv);
        }
    }

    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    isValidPhone(phone) {
        return /^[\+]?[1-9][\d]{0,15}$/.test(phone.replace(/\s/g, ''));
    }

    sortTable(header) {
        const table = header.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const columnIndex = Array.from(header.parentElement.children).indexOf(header);
        const isAscending = header.classList.contains('sort-asc');

        rows.sort((a, b) => {
            const aValue = a.children[columnIndex].textContent.trim();
            const bValue = b.children[columnIndex].textContent.trim();
            
            if (isAscending) {
                return bValue.localeCompare(aValue);
            } else {
                return aValue.localeCompare(bValue);
            }
        });

        // Update table
        rows.forEach(row => tbody.appendChild(row));

        // Update header state
        header.classList.toggle('sort-asc');
        header.classList.toggle('sort-desc');
    }

    updateBulkActions() {
        const selectedCount = document.querySelectorAll('.table-modern tbody input[type="checkbox"]:checked').length;
        const bulkActions = document.querySelector('.bulk-actions');
        
        if (bulkActions) {
            bulkActions.style.display = selectedCount > 0 ? 'flex' : 'none';
            bulkActions.querySelector('.selected-count').textContent = selectedCount;
        }
    }

    openModal(modalId) {
        const modal = document.querySelector(modalId);
        if (modal) {
            modal.style.display = 'block';
            modal.classList.add('show');
            document.body.classList.add('modal-open');
            
            // Focus first input
            const firstInput = modal.querySelector('input, textarea, select');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 300);
            }
        }
    }

    closeModal() {
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            openModal.classList.remove('show');
            setTimeout(() => {
                openModal.style.display = 'none';
                document.body.classList.remove('modal-open');
            }, 300);
        }
    }

    autoSaveForm(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        
        // Save to localStorage as backup
        localStorage.setItem(`form_${form.id}`, JSON.stringify(data));
        
        // Show auto-save notification
        this.showNotification('Form auto-saved', 'success', 2000);
    }

    saveCurrentForm() {
        const activeForm = document.querySelector('form:focus-within');
        if (activeForm) {
            this.autoSaveForm(activeForm);
        }
    }

    createNewItem() {
        const newButtons = document.querySelectorAll('[data-bs-toggle="modal"][data-bs-target*="add"]');
        if (newButtons.length > 0) {
            newButtons[0].click();
        }
    }

    focusSearch() {
        const searchInput = document.querySelector('input[type="search"], input[placeholder*="search"], #searchFilter');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }

    exportData() {
        const exportButtons = document.querySelectorAll('.btn[onclick*="export"], .btn-outline-primary');
        if (exportButtons.length > 0) {
            exportButtons[0].click();
        }
    }
}

// Initialize Modern UI when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.modernUI = new ModernUI();
});

// Export for global access
window.ModernUI = ModernUI; 