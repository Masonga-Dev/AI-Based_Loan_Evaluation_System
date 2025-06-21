// Custom JavaScript for AI-Based Loan Evaluation System

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // File upload drag and drop functionality
    setupFileUpload();

    // Form validation
    setupFormValidation();

    // AJAX setup for CSRF token
    setupAjaxCSRF();

    // Initialize data tables if present
    if ($.fn.DataTable) {
        $('.data-table').DataTable({
            responsive: true,
            pageLength: 25,
            order: [[0, 'desc']],
            language: {
                search: "Search applications:",
                lengthMenu: "Show _MENU_ applications per page",
                info: "Showing _START_ to _END_ of _TOTAL_ applications",
                paginate: {
                    first: "First",
                    last: "Last",
                    next: "Next",
                    previous: "Previous"
                }
            }
        });
    }
});

// File Upload Functionality
function setupFileUpload() {
    $('.file-upload-area').on('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).addClass('dragover');
    });

    $('.file-upload-area').on('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
    });

    $('.file-upload-area').on('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
        
        var files = e.originalEvent.dataTransfer.files;
        handleFileUpload(files, $(this));
    });

    $('.file-upload-area').on('click', function() {
        $(this).find('input[type="file"]').click();
    });

    $('input[type="file"]').on('change', function() {
        var files = this.files;
        handleFileUpload(files, $(this).closest('.file-upload-area'));
    });
}

// Handle file upload
function handleFileUpload(files, uploadArea) {
    if (files.length > 0) {
        var file = files[0];
        var maxSize = 10 * 1024 * 1024; // 10MB
        var allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];

        if (file.size > maxSize) {
            showAlert('File size must be less than 10MB', 'danger');
            return;
        }

        if (!allowedTypes.includes(file.type)) {
            showAlert('Only PDF, JPG, and PNG files are allowed', 'danger');
            return;
        }

        // Update UI to show selected file
        uploadArea.find('.upload-text').text('File selected: ' + file.name);
        uploadArea.addClass('file-selected');
        
        // Show upload progress
        showUploadProgress(uploadArea);
    }
}

// Show upload progress
function showUploadProgress(uploadArea) {
    var progressHtml = `
        <div class="upload-progress mt-3">
            <div class="progress">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 0%"></div>
            </div>
            <small class="text-muted">Uploading...</small>
        </div>
    `;
    uploadArea.append(progressHtml);

    // Simulate upload progress
    var progress = 0;
    var interval = setInterval(function() {
        progress += Math.random() * 15;
        if (progress >= 100) {
            progress = 100;
            clearInterval(interval);
            uploadArea.find('.upload-progress small').text('Upload complete!');
            setTimeout(function() {
                uploadArea.find('.upload-progress').fadeOut();
            }, 2000);
        }
        uploadArea.find('.progress-bar').css('width', progress + '%');
    }, 200);
}

// Form validation
function setupFormValidation() {
    // Real-time validation for loan amount
    $('#id_loan_amount').on('input', function() {
        var amount = parseFloat($(this).val());
        var minAmount = 1000;
        var maxAmount = 1000000;

        if (amount < minAmount) {
            showFieldError($(this), 'Minimum loan amount is $' + minAmount.toLocaleString());
        } else if (amount > maxAmount) {
            showFieldError($(this), 'Maximum loan amount is $' + maxAmount.toLocaleString());
        } else {
            clearFieldError($(this));
            updateMonthlyPayment();
        }
    });

    // Real-time validation for income
    $('#id_annual_income').on('input', function() {
        var income = parseFloat($(this).val());
        if (income > 0) {
            clearFieldError($(this));
            calculateDebtToIncomeRatio();
        }
    });

    // Calculate monthly payment estimate
    $('#id_loan_term_months, #id_interest_rate').on('input', updateMonthlyPayment);
}

// Show field error
function showFieldError(field, message) {
    field.addClass('is-invalid');
    var errorDiv = field.next('.invalid-feedback');
    if (errorDiv.length === 0) {
        field.after('<div class="invalid-feedback">' + message + '</div>');
    } else {
        errorDiv.text(message);
    }
}

// Clear field error
function clearFieldError(field) {
    field.removeClass('is-invalid');
    field.next('.invalid-feedback').remove();
}

// Update monthly payment calculation
function updateMonthlyPayment() {
    var amount = parseFloat($('#id_loan_amount').val()) || 0;
    var term = parseInt($('#id_loan_term_months').val()) || 0;
    var rate = parseFloat($('#id_interest_rate').val()) || 0;

    if (amount > 0 && term > 0 && rate > 0) {
        var monthlyRate = rate / 100 / 12;
        var payment = amount * (monthlyRate * Math.pow(1 + monthlyRate, term)) / 
                     (Math.pow(1 + monthlyRate, term) - 1);
        
        $('#monthly-payment-estimate').text('$' + payment.toFixed(2));
        $('#payment-estimate-container').show();
    } else {
        $('#payment-estimate-container').hide();
    }
}

// Calculate debt-to-income ratio
function calculateDebtToIncomeRatio() {
    var income = parseFloat($('#id_annual_income').val()) || 0;
    var monthlyDebt = parseFloat($('#id_monthly_debt_payments').val()) || 0;

    if (income > 0 && monthlyDebt > 0) {
        var monthlyIncome = income / 12;
        var ratio = (monthlyDebt / monthlyIncome) * 100;
        
        $('#debt-to-income-ratio').text(ratio.toFixed(1) + '%');
        $('#ratio-container').show();

        // Color code the ratio
        var ratioElement = $('#debt-to-income-ratio');
        if (ratio <= 28) {
            ratioElement.removeClass().addClass('text-success');
        } else if (ratio <= 36) {
            ratioElement.removeClass().addClass('text-warning');
        } else {
            ratioElement.removeClass().addClass('text-danger');
        }
    }
}

// AJAX CSRF setup
function setupAjaxCSRF() {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    var csrftoken = getCookie('csrftoken');

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
}

// Show alert message
function showAlert(message, type) {
    var alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    if ($('.alert-container').length > 0) {
        $('.alert-container').prepend(alertHtml);
    } else {
        $('main .container').prepend('<div class="alert-container">' + alertHtml + '</div>');
    }

    // Auto-hide after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
}

// Loading state management
function showLoading(element) {
    element.prop('disabled', true);
    element.html('<span class="loading-spinner"></span> Loading...');
}

function hideLoading(element, originalText) {
    element.prop('disabled', false);
    element.html(originalText);
}

// Confirmation dialogs
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Format percentage
function formatPercentage(value) {
    return (value * 100).toFixed(2) + '%';
}
