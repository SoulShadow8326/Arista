import Dropdown from '../components/dropdown.js';

/**
 * Initialize dropdowns on the page
 * @param {HTMLElement} [container=document] - Container to search for dropdowns in
 * @returns {Object} Object containing all initialized dropdown instances
 */
function initDropdowns(container = document) {
    const dropdowns = {};
    
    container.querySelectorAll('[data-dropdown]').forEach((dropdownEl, index) => {
        const id = dropdownEl.id || `dropdown-${index}`;
        dropdownEl.id = id;
        
        const options = {
            position: dropdownEl.dataset.dropdownPosition || 'bottom-start',
            trigger: dropdownEl.dataset.dropdownTrigger || 'click',
            closeOnClickOutside: dropdownEl.dataset.dropdownCloseOnClickOutside !== 'false',
            closeOnSelect: dropdownEl.dataset.dropdownCloseOnSelect !== 'false',
            autoClose: dropdownEl.dataset.dropdownAutoClose !== 'false'
        };
        
        dropdowns[id] = new Dropdown(dropdownEl, options);
    });
    
    return dropdowns;
}

/**
 * Create a dropdown menu with the given options
 * @param {Object} options - Dropdown options
 * @param {string} options.id - Unique ID for the dropdown
 * @param {string} options.trigger - HTML for the dropdown trigger
 * @param {Array} options.items - Array of menu items
 * @param {string} options.position - Position of the dropdown (top-start, top-end, bottom-start, bottom-end)
 * @param {string} options.triggerClass - Additional classes for the trigger
 * @param {string} options.menuClass - Additional classes for the menu
 * @param {HTMLElement} options.parent - Parent element to append the dropdown to
 * @returns {Object} Object containing the dropdown instance and its elements
 */
function createDropdown({
    id,
    trigger = 'Select an option',
    items = [],
    position = 'bottom-start',
    triggerClass = '',
    menuClass = '',
    parent = document.body
}) {
    const dropdownEl = document.createElement('div');
    dropdownEl.className = `dropdown ${triggerClass}`;
    dropdownEl.id = id;
    dropdownEl.dataset.dropdown = '';
    dropdownEl.dataset.dropdownPosition = position;
    
    const triggerEl = document.createElement('button');
    triggerEl.className = 'dropdown-trigger';
    triggerEl.dataset.dropdownTrigger = '';
    triggerEl.innerHTML = `${trigger} <span class="dropdown-arrow">▼</span>`;
    
    const menuEl = document.createElement('div');
    menuEl.className = `dropdown-menu ${menuClass}`.trim();
    menuEl.dataset.dropdownMenu = '';
    
    items.forEach(item => {
        if (item === 'divider') {
            menuEl.appendChild(document.createElement('hr'));
            return;
        }
        
        if (item.header) {
            const header = document.createElement('div');
            header.className = 'dropdown-header';
            header.textContent = item.header;
            menuEl.appendChild(header);
            return;
        }
        
        const itemEl = document.createElement(item.href ? 'a' : 'button');
        itemEl.className = `dropdown-item ${item.className || ''} ${item.danger ? 'dropdown-item-danger' : ''}`.trim();
        itemEl.role = 'menuitem';
        
        if (item.href) itemEl.href = item.href;
        if (item.id) itemEl.dataset.id = item.id;
        if (item.onClick) itemEl.addEventListener('click', item.onClick);
        if (item.disabled) itemEl.disabled = true;
        
        if (item.icon) {
            const icon = document.createElement('span');
            icon.className = `dropdown-item-icon ${item.icon}`;
            itemEl.appendChild(icon);
        }
        
        const text = document.createElement('span');
        text.className = 'dropdown-item-text';
        text.textContent = item.text;
        itemEl.appendChild(text);
        
        menuEl.appendChild(itemEl);
    });
    
    dropdownEl.appendChild(triggerEl);
    dropdownEl.appendChild(menuEl);
    
    parent.appendChild(dropdownEl);
    
    const dropdown = new Dropdown(dropdownEl, {
        position,
        trigger: 'click',
        closeOnClickOutside: true,
        closeOnSelect: true,
        autoClose: true
    });
    
    return {
        element: dropdownEl,
        trigger: triggerEl,
        menu: menuEl,
        instance: dropdown,
        destroy: () => {
            dropdown.destroy();
            dropdownEl.remove();
        }
    };
}
document.addEventListener('DOMContentLoaded', () => {
    initDropdowns();
});

export { Dropdown, initDropdowns, createDropdown };
