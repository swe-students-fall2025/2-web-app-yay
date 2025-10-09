// Shared utilities
let categories = [
    { id: 1, name: 'Work', color: 'bg-gray-600', customColor: '#4b5563' },
    { id: 2, name: 'Personal', color: 'bg-gray-500', customColor: '#6b7280' },
    { id: 3, name: 'Shopping', color: 'bg-gray-700', customColor: '#374151' },
    { id: 4, name: 'Health', color: 'bg-gray-800', customColor: '#1f2937' }
];

export const colorOptions = [
    { name: 'Dark Gray', value: '#1f2937', bgClass: 'bg-gray-800' },
    { name: 'Gray', value: '#374151', bgClass: 'bg-gray-700' },
    { name: 'Medium Gray', value: '#4b5563', bgClass: 'bg-gray-600' },
    { name: 'Light Gray', value: '#6b7280', bgClass: 'bg-gray-500' },
    { name: 'Lighter Gray', value: '#9ca3af', bgClass: 'bg-gray-400' },
    { name: 'Blue', value: '#3b82f6', bgClass: 'bg-blue-500' },
    { name: 'Green', value: '#10b981', bgClass: 'bg-green-500' },
    { name: 'Red', value: '#ef4444', bgClass: 'bg-red-500' },
    { name: 'Purple', value: '#8b5cf6', bgClass: 'bg-purple-500' },
    { name: 'Orange', value: '#f97316', bgClass: 'bg-orange-500' }
];

export function getCategories() {
    const saved = localStorage.getItem('categories');
    if (saved) {
        try {
            categories = JSON.parse(saved);
        } catch (e) {
            console.log('Using default categories');
        }
    }
    return categories;
}

export function saveCategories(newCategories) {
    categories = newCategories;
    localStorage.setItem('categories', JSON.stringify(categories));
}

export function getCategoryByName(name) {
    return getCategories().find(cat => cat.name === name);
}

export function updateCategoryColor(categoryId, colorValue) {
    const cats = getCategories();
    const category = cats.find(cat => cat.id === categoryId);
    if (category) {
        category.customColor = colorValue;
        const colorOption = colorOptions.find(opt => opt.value === colorValue);
        if (colorOption) {
            category.color = colorOption.bgClass;
        }
        saveCategories(cats);
    }
}

export function getPriorityBadgeClasses(priority) {
    switch (priority) {
        case 'High': return 'bg-gray-200 text-gray-800';
        case 'Medium': return 'bg-gray-100 text-gray-700';
        case 'Low': return 'bg-gray-50 text-gray-600';
        default: return 'bg-gray-100 text-gray-700';
    }
}

export function formatDisplayDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function toggleSelectedButtonStyles(buttons, targetButton, selectedClasses, unselectedClasses) {
    buttons.forEach((btn) => {
        btn.classList.remove(...selectedClasses);
        btn.classList.add(...unselectedClasses);
    });
    targetButton.classList.remove(...unselectedClasses);
    targetButton.classList.add(...selectedClasses);
}


