// main.js - Funciones globales para la plataforma

// Mostrar/ocultar loading spinner
function showLoading() {
    let spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinner.id = 'loading-spinner';
    spinner.style.position = 'fixed';
    spinner.style.top = '50%';
    spinner.style.left = '50%';
    spinner.style.transform = 'translate(-50%, -50%)';
    spinner.style.zIndex = '9999';
    document.body.appendChild(spinner);
}

function hideLoading() {
    let spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

// Formatear fechas
function formatDate(dateString) {
    let date = new Date(dateString);
    return date.toLocaleDateString('es-CL', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Validar email
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Validar teléfono chileno (ejemplo)
function validatePhone(phone) {
    const re = /^(\+?56)?[ -]?9[ -]?\d{4}[ -]?\d{4}$/;
    return re.test(phone);
}

// Mostrar notificaciones
function showNotification(message, type = 'info') {
    let alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    // Auto-cerrar después de 5 segundos
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Función para hacer peticiones AJAX
async function fetchAPI(url, options = {}) {
    try {
        showLoading();
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error en la conexión', 'danger');
        throw error;
    } finally {
        hideLoading();
    }
}

// Inicializar tooltips de Bootstrap
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Agregar clase fade-in a elementos con la clase
    document.querySelectorAll('.fade-in').forEach(el => {
        el.classList.add('fade-in');
    });
});

// Función para compartir en redes sociales
function shareOnWhatsApp(text) {
    let url = `https://wa.me/?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

function shareOnTwitter(text) {
    let url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

function shareOnFacebook(url) {
    let shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
    window.open(shareUrl, '_blank');
}

// Detectar si el usuario está inactivo
let inactivityTime = function() {
    let time;
    window.onload = resetTimer;
    document.onmousemove = resetTimer;
    document.onkeypress = resetTimer;
    document.onscroll = resetTimer;
    document.onclick = resetTimer;

    function logout() {
        // Redirigir a logout después de 30 minutos de inactividad
        if (confirm('¿Sigues ahí? Por seguridad, cerraremos tu sesión por inactividad.')) {
            window.location.href = '/logout';
        } else {
            resetTimer();
        }
    }

    function resetTimer() {
        clearTimeout(time);
        time = setTimeout(logout, 30 * 60 * 1000); // 30 minutos
    }
};

// Activar detección de inactividad solo si el usuario está logueado
if (document.querySelector('.user-logged')) {
    inactivityTime();
}

// Función para imprimir
function printElement(elementId) {
    let element = document.getElementById(elementId);
    let printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
            <head>
                <title>Imprimir</title>
                <link rel="stylesheet" href="/static/css/style.css">
            </head>
            <body>
                ${element.outerHTML}
            </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.print();
}

// Función para descargar como PDF (requiere librería externa)
function downloadAsPDF(elementId, filename = 'documento.pdf') {
    alert('Función de descarga PDF en desarrollo. Próximamente disponible.');
}

// Manejar el botón de "Volver arriba"
window.onscroll = function() {
    let backToTop = document.getElementById('back-to-top');
    if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
        backToTop.style.display = 'block';
    } else {
        backToTop.style.display = 'none';
    }
};

function scrollToTop() {
    document.body.scrollTop = 0;
    document.documentElement.scrollTop = 0;
}

// Agregar botón de "Volver arriba"
document.addEventListener('DOMContentLoaded', function() {
    let backToTop = document.createElement('button');
    backToTop.id = 'back-to-top';
    backToTop.innerHTML = '<i class="fas fa-arrow-up"></i>';
    backToTop.style.position = 'fixed';
    backToTop.style.bottom = '20px';
    backToTop.style.right = '20px';
    backToTop.style.display = 'none';
    backToTop.style.zIndex = '99';
    backToTop.style.border = 'none';
    backToTop.style.borderRadius = '50%';
    backToTop.style.width = '50px';
    backToTop.style.height = '50px';
    backToTop.style.backgroundColor = '#007bff';
    backToTop.style.color = 'white';
    backToTop.style.cursor = 'pointer';
    backToTop.onclick = scrollToTop;
    document.body.appendChild(backToTop);
});