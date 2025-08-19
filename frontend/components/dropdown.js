class Dropdown {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            position: 'bottom-start',
            trigger: 'click', 
            closeOnClickOutside: true,
            closeOnSelect: true,
            autoClose: true,
            ...options
        };
        
        this.isOpen = false;
        this.init();
    }
    
    init() {
        this.trigger = this.container.querySelector('[data-dropdown-trigger]');
        this.menu = this.container.querySelector('[data-dropdown-menu]');
        
        if (!this.trigger || !this.menu) {
            console.error('Dropdown: Missing required elements (trigger or menu)');
            return;
        }
        
        this.setupEventListeners();
        this.setupPosition();
    }
    
    setupEventListeners() {
        if (this.options.trigger === 'click') {
            this.trigger.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggle();
            });
        } else if (this.options.trigger === 'hover') {
            this.container.addEventListener('mouseenter', () => this.open());
            this.container.addEventListener('mouseleave', () => this.close());
        }
        
        if (this.options.closeOnClickOutside) {
            document.addEventListener('click', this.handleClickOutside.bind(this));
        }
        
        if (this.options.closeOnSelect) {
            this.menu.querySelectorAll('a, button, [role="menuitem"]').forEach(item => {
                item.addEventListener('click', () => {
                    if (this.options.autoClose) {
                        this.close();
                    }
                });
            });
        }
    }
    
    handleClickOutside(e) {
        if (!this.container.contains(e.target) && this.isOpen) {
            this.close();
        }
    }
    
    setupPosition() {
        this.container.style.position = 'relative';
        this.menu.style.position = 'absolute';
        this.menu.style.zIndex = '1000';
        this.menu.style.display = 'none';
        
        switch (this.options.position) {
            case 'top-start':
                this.menu.style.bottom = '100%';
                this.menu.style.left = '0';
                this.menu.style.marginBottom = '8px';
                break;
            case 'top-end':
                this.menu.style.bottom = '100%';
                this.menu.style.right = '0';
                this.menu.style.marginBottom = '8px';
                break;
            case 'bottom-start':
                this.menu.style.top = '100%';
                this.menu.style.left = '0';
                this.menu.style.marginTop = '8px';
                break;
            case 'bottom-end':
                this.menu.style.top = '100%';
                this.menu.style.right = '0';
                this.menu.style.marginTop = '8px';
                break;
            default:
                this.menu.style.top = '100%';
                this.menu.style.left = '0';
                this.menu.style.marginTop = '8px';
        }
    }
    
    open() {
        if (this.isOpen) return;
        
        this.menu.style.display = 'block';
        this.container.classList.add('dropdown-open');
        this.isOpen = true;
        
        document.querySelectorAll('.dropdown-open').forEach(dropdown => {
            if (dropdown !== this.container) {
                dropdown.classList.remove('dropdown-open');
                const menu = dropdown.querySelector('[data-dropdown-menu]');
                if (menu) menu.style.display = 'none';
            }
        });
        
        this.container.dispatchEvent(new CustomEvent('dropdown:open', { bubbles: true }));
    }
    
    close() {
        if (!this.isOpen) return;
        
        this.menu.style.display = 'none';
        this.container.classList.remove('dropdown-open');
        this.isOpen = false;
        
        this.container.dispatchEvent(new CustomEvent('dropdown:close', { bubbles: true }));
    }
    
    toggle() {
        this.isOpen ? this.close() : this.open();
    }
    
    updatePosition() {
        this.setupPosition();
    }
    
    destroy() {
        this.trigger.removeEventListener('click', this.toggle);
        document.removeEventListener('click', this.handleClickOutside);
        this.container.style.position = '';
        this.menu.style = '';
        this.container.classList.remove('dropdown-open');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-dropdown]').forEach(container => {
        const options = {
            position: container.dataset.dropdownPosition || 'bottom-start',
            trigger: container.dataset.dropdownTrigger || 'click',
            closeOnClickOutside: container.dataset.dropdownCloseOnClickOutside !== 'false',
            closeOnSelect: container.dataset.dropdownCloseOnSelect !== 'false',
            autoClose: container.dataset.dropdownAutoClose !== 'false'
        };
        
        new Dropdown(container, options);
    });
});

export default Dropdown;
