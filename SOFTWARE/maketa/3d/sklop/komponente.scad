// Simplified models of the purchased components (for the assembly, not for printing).
// Dimensions from the usual datasheets / measured modules, rounded to 0.5 mm.
// Used by sklop_makete.scad; rendering this file on its own shows every component side by side.
//
// Every model calls dio("<colour group>") instead of color(): the assembly uses it to colour the parts and to
// export one colour group at a time (see izvoz.py).

use <../drzac_tablice.scad>

font = "DejaVu Sans:style=Bold";
demo = true;            // sklop_makete.scad sets this to false

// colour groups -> RGB; the same table is used by izvoz.py for the coloured GLB
BOJE = [
    ["baza", "#e3e6ea"], ["forex", "#f7f8f9"], ["asfalt", "#5c6168"], ["bijela", "#ffffff"],
    ["crvena", "#d32f2f"], ["zelena", "#7cb342"], ["pla", "#f39c12"], ["pcb_plava", "#1f5fa8"],
    ["pcb_crna", "#26282b"], ["pcb_zelena", "#2e7d32"], ["srebrna", "#b9bec4"], ["servo", "#3d6fd6"],
    ["crna", "#1b1c1e"], ["tamno_siva", "#3a3d42"], ["staklo", "#22313f"], ["led_zelena", "#39ff6a"],
    ["led_crvena", "#ff3b3b"], ["zuta", "#f2c200"], ["auto_crveni", "#c62828"], ["auto_plavi", "#1565c0"],
    ["auto_zuti", "#f9a825"], ["auto_srebrni", "#cfd8dc"], ["guma", "#121212"], ["plava_eu", "#0d47a1"],
];
grupa = "sve";          // "sve" = everything in colour; a group name = only that group (for STL export)

function boja(name) = BOJE[search([name], BOJE)[0]][1];

module dio(name) {
    if (grupa == "sve") color(boja(name)) children();
    else if (grupa == name) children();
}

// ------------------------------------------------------------------ sensors and actuators
// HC-SR04: origin = centre of the PCB, PCB in the XY plane, transducers pointing DOWN (-Z).
module hc_sr04() {
    dio("pcb_plava") translate([-22.5, -10, 0]) cube([45, 20, 1.6]);
    for (s = [-1, 1]) {
        dio("srebrna") translate([s * 13, 0, -12]) cylinder(d = 16, h = 12, $fn = 32);
        dio("crna") translate([s * 13, 0, -12.2]) cylinder(d = 13, h = 0.4, $fn = 32);   // mesh
    }
    dio("srebrna") translate([-5.5, -2, 1.6]) cube([11, 4, 3.5]);                       // crystal
    dio("crna") translate([-5, 8, 1.6]) cube([10, 2.5, 2.5]);                           // header
    for (i = [0:3]) dio("srebrna") translate([-3.8 + i * 2.54, 9, 1.6 + 1.2]) rotate([-90, 0, 0])
        cylinder(d = 0.7, h = 7, $fn = 8);
}

// SG90 micro servo: body centred in XY, bottom at z = 0, long axis X, output shaft at x = +5.5, pointing UP.
module sg90() {
    dio("servo") {
        translate([-11.4, -6.1, 0]) cube([22.8, 12.2, 22.5]);
        translate([-16.1, -6.1, 15.9]) difference() {                                   // mounting tabs
            cube([32.2, 12.2, 2.5]);
            for (x = [2.3, 29.9]) translate([x, 6.1, -1]) cylinder(d = 2, h = 5, $fn = 12);
        }
        translate([5.5, 0, 22.5]) cylinder(d = 11.8, h = 4, $fn = 32);                  // gear housing
        translate([-0.5, 0, 22.5]) cylinder(d = 5.5, h = 4, $fn = 20);
    }
    dio("bijela") translate([5.5, 0, 26.5]) cylinder(d = 4.8, h = 3.2, $fn = 20);       // output shaft
    for (i = [0:2]) dio(["crna", "crvena", "zuta"][i])                                  // cable
        translate([-11.4, -1.2 + i * 1.2, 4]) rotate([0, -90, 0]) cylinder(d = 1.1, h = 12, $fn = 8);
}

// FC-51 IR obstacle sensor standing in nosac_ir: PCB vertical (thin in X), IR LEDs at the top looking +X.
module fc51() {
    dio("pcb_plava") translate([-0.8, -7.25, 3]) cube([1.6, 14.5, 31.5]);
    dio("bijela") translate([0.8, -2.5, 26]) cube([1, 5, 8]);
    for (y = [-3.6, 3.6]) dio(y < 0 ? "bijela" : "crna")
        translate([0.8, y, 30]) rotate([0, 90, 0]) { cylinder(d = 5, h = 5, $fn = 20); translate([0, 0, 5]) sphere(d = 5, $fn = 20); }
    dio("servo") translate([-4.6, -3, 14]) cube([3.8, 6.5, 6.5]);                       // potentiometer
}

// USB webcam: body centred at the origin, base at z = 0, lens looking +Y.
module usb_kamera() {
    dio("tamno_siva") hull() for (x = [-26, 26]) translate([x, 0, 11]) rotate([90, 0, 0])
        cylinder(d = 22, h = 18, center = true, $fn = 32);
    dio("staklo") translate([0, 9, 11]) rotate([-90, 0, 0]) cylinder(d = 14, h = 2, $fn = 32);
    dio("srebrna") translate([0, 8.5, 11]) rotate([-90, 0, 0]) difference() {
        cylinder(d = 17, h = 1.5, $fn = 32); translate([0, 0, -1]) cylinder(d = 14, h = 4, $fn = 32);
    }
    dio("led_zelena") translate([14, 9, 15]) sphere(d = 2, $fn = 12);
}

// WS2812 single-LED module (round PCB), LED looking +Y; lit = colour of the spot state.
module led_ws2812(stanje = "led_zelena") {
    dio("pcb_crna") rotate([-90, 0, 0]) cylinder(d = 10, h = 1.6, $fn = 24);
    dio(stanje) translate([-2.5, 1.6, -2.5]) cube([5, 1.6, 5]);
}

// 5 mm LED looking +Y
module led5(stanje) {
    dio(stanje) rotate([-90, 0, 0]) { cylinder(d = 5, h = 5.5, $fn = 20); translate([0, 0, 5.5]) sphere(d = 5, $fn = 20); }
    dio(stanje) rotate([-90, 0, 0]) cylinder(d = 5.8, h = 1, $fn = 20);
}

// 6x6 tactile button with a 12x12 cap
module tipkalo(kapica = "crvena") {
    dio("crna") translate([-6, -6, 0]) cube([12, 12, 3.5]);
    dio(kapica) translate([0, 0, 3.5]) cylinder(d = 10, h = 3, $fn = 24);
}

// ESP32 DevKit V1 (30 pin) on its pin headers: origin = PCB centre at floor level, long axis X, USB at -X.
module esp32_devkit() {
    z = 9;                                                                              // header height
    dio("pcb_crna") translate([-25.5, -14, z]) cube([51, 28, 1.6]);
    dio("srebrna") translate([7, -9, z + 1.6]) cube([17.5, 18, 3.1]);                  // ESP-WROOM-32 can
    dio("pcb_crna") translate([18, -9, z + 1.6]) cube([7, 18, 1]);                     // antenna
    dio("srebrna") translate([-27, -4, z + 1.6]) cube([6, 8, 3]);                      // micro USB
    for (y = [-12.7, 12.7]) {
        dio("crna") translate([-19, y - 1.25, 0]) cube([38, 2.5, z]);
        for (i = [0:14]) dio("srebrna") translate([-17.8 + i * 2.54, y, z + 1.6]) cylinder(d = 0.9, h = 1.5, $fn = 8);
    }
    for (x = [-17, -12]) dio("crna") translate([x, 9, z + 1.6]) cube([3, 3, 1.5]);     // EN / BOOT
}

// Raspberry Pi 4 (edge computer): origin = PCB corner at floor level, on 5 mm feet.
module raspberry_pi() {
    z = 5;
    for (x = [3.5, 61.5]) for (y = [3.5, 52.5]) dio("crna") translate([x, y, 0]) cylinder(d = 5, h = z, $fn = 16);
    dio("pcb_zelena") translate([0, 0, z]) cube([85, 56, 1.4]);
    dio("srebrna") translate([65, 2, z + 1.4]) cube([21, 16, 13.5]);                   // ethernet
    for (y = [22, 38]) dio("srebrna") translate([69, y, z + 1.4]) cube([17.5, 14.5, 16]); // USB
    dio("srebrna") translate([22, 22, z + 1.4]) cube([15, 15, 2.4]);                   // SoC
    dio("crna") translate([7, 50, z + 1.4]) cube([51, 5, 8.5]);                        // GPIO header
}

// 5 V / 4 A power brick with rocker switch
module napajanje() {
    dio("crna") translate([0, 0, 0]) cube([60, 30, 22]);
    dio("crna") translate([60, 12, 8]) rotate([0, 90, 0]) cylinder(d = 5, h = 25, $fn = 12);
    dio("crvena") translate([10, -4, 6]) cube([12, 4, 10]);
}

// ------------------------------------------------------------------ 1:24 toy car
// Origin = centre of the car on the floor, driving direction +X. The printed plate holder (drzac_tablice)
// with a fictional plate sits on the front bumper, looking +X.
module autic(boja_auta = "auto_crveni", tablica = "ZG 1234-AB") {
    L = 183; B = 76;
    dio(boja_auta) {
        hull() for (x = [-L / 2 + 8, L / 2 - 8]) for (y = [-B / 2 + 8, B / 2 - 8])
            translate([x, y, 9]) cylinder(r = 8, h = 25, $fn = 24);
        hull() for (x = [-50, 22]) for (y = [-B / 2 + 11, B / 2 - 11])                  // cabin
            translate([x, y, 34]) cylinder(r = 6, h = 1, $fn = 20);
        hull() for (x = [-42, 12]) for (y = [-B / 2 + 14, B / 2 - 14])
            translate([x, y, 53]) cylinder(r = 6, h = 3, $fn = 20);
    }
    dio("staklo") {
        hull() { translate([22, -24, 35]) cube([4, 48, 1]); translate([12, -22, 53]) cube([4, 44, 1]); }   // windscreen
        for (s = [-1, 1]) translate([-36, s * (B / 2 - 9.5) - 0.5, 38]) cube([52, 1, 12]);                  // side windows
    }
    for (x = [-L / 2 + 32, L / 2 - 32]) for (s = [-1, 1]) {
        dio("guma") translate([x, s * (B / 2 - 6), 13.5]) rotate([90, 0, 0]) cylinder(d = 27, h = 11, center = true, $fn = 28);
        dio("srebrna") translate([x, s * (B / 2 - 0.3), 13.5]) rotate([90, 0, 0]) cylinder(d = 15, h = 1, center = true, $fn = 20);
    }
    for (s = [-1, 1]) dio("zuta") translate([L / 2 - 1, s * 26, 26]) rotate([0, 90, 0]) cylinder(d = 8, h = 2, $fn = 16);
    // plate holder + printed plate, standing on the front bumper
    translate([L / 2, 0, 12]) rotate([90, 0, 90]) {
        translate([-(60.5 + 3) / 2, 0, 0]) dio("pla") drzac_tablice();
        translate([-30.25 + 1.5 - 1.5, 1.5, 1.45]) {
            dio("bijela") cube([60.5, 13.2, 0.3]);
            dio("plava_eu") cube([5, 13.2, 0.4]);
            dio("crna") translate([33, 6.6, 0.3]) linear_extrude(0.3)
                text(tablica, size = 6.6 * min(1, 9 / len(tablica)), font = font, halign = "center", valign = "center");
        }
    }
}

// ------------------------------------------------------------------ demo: every component with its name
module _demo() {
    module label(t, x, y) dio("crna") translate([x, y, 0]) linear_extrude(0.4)
        text(t, size = 4.5, font = font, halign = "center");
    translate([0, 0, 12]) hc_sr04();                  label("HC-SR04", 0, -22);
    translate([60, 0, 0]) sg90();                     label("SG90", 60, -22);
    translate([105, 0, 0]) fc51();                    label("FC-51", 105, -22);
    translate([160, 0, 0]) usb_kamera();              label("USB kamera", 160, -22);
    translate([225, 0, 5]) led_ws2812("led_crvena");  label("WS2812", 225, -22);
    translate([265, 0, 5]) led5("led_zelena");        label("LED 5 mm", 265, -22);
    translate([305, 0, 0]) tipkalo();                 label("tipkalo", 305, -22);
    translate([25, -85, 0]) esp32_devkit();           label("ESP32 DevKit", 25, -112);
    translate([80, -115, 0]) raspberry_pi();          label("Raspberry Pi", 122, -128);
    translate([195, -105, 0]) napajanje();            label("napajanje 5 V", 225, -120);
    translate([160, 95, 0]) autic();                  label("autic 1:24 s drzacem tablice", 160, 45);
}
if (demo) _demo();
