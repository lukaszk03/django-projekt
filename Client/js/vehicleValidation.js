// Master/Client/js/vehicleValidation.js

/**
 * Funkcja walidująca numer VIN na poziomie Front-endu (Warstwa Prezentacji).
 * Realizuje Poprawkę dla ERR-04.
 */
function validateVinFrontend(vinValue) {
    // 1. Sprawdzenie, czy wartość jest pusta
    if (!vinValue) {
        return "Numer VIN jest wymagany.";
    }

    // 2. Walidacja ERR-04: Sprawdzenie długości (musi mieć dokładnie 17 znaków)
    if (vinValue.length !== 17) {
        return "Błąd ERR-04: Numer VIN musi składać się z dokładnie 17 znaków.";
    }

    // 3. Walidacja ERR-04: Sprawdzenie, czy zawiera tylko znaki alfanumeryczne
    if (!/^[a-z0-9]+$/i.test(vinValue)) {
        return "Błąd ERR-04: Numer VIN może zawierać tylko litery i cyfry.";
    }

    // 4. Jeśli wszystko jest w porządku, zwracamy brak błędu
    return null; 
}

// --- TESTY (DO URUCHOMIENIA W KONSOLI) ---

console.log("--- WERYFIKACJA POPRAWKI ERR-04 ---");
// Test, który powinien zwrócić BŁĄD długości:
console.log("TEST 1: Za krótki VIN:", validateVinFrontend("12345"));

// Test, który powinien zwrócić BŁĄD formatu:
console.log("TEST 2: VIN z niedozwolonym znakiem:", validateVinFrontend("1ABC234567890DE F1")); 

// Test, który powinien zwrócić null (SUKCES):
console.log("TEST 3: Prawidłowy VIN:", validateVinFrontend("1ABC234567890DEF1"));