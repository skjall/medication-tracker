// Import Bootstrap CSS and JS
import 'bootstrap/dist/css/bootstrap.min.css';
import * as bootstrap from 'bootstrap';

// Import Font Awesome
import '@fortawesome/fontawesome-free/css/all.min.css';

// Import jQuery and make it available globally
import $ from 'jquery';
window.jQuery = $;
window.$ = $;

// Import Popper.js (required by Bootstrap)
import * as Popper from '@popperjs/core';
window.Popper = Popper;

// Make Bootstrap available globally
window.bootstrap = bootstrap;

console.log('Vendor libraries loaded: Bootstrap, Font Awesome, jQuery');