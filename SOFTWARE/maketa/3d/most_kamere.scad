// Camera bridge over a lane: two legs + crossbar + tilting camera plate.
// The lens ends up ~130 mm above the floor, the plate tilts 0-40 deg (M3 screw as hinge).
// Webcam clip or strap goes through the slots; for a 1/4" tripod thread drill the centre hole to 6.5 mm.
part = "all";              // "leg" | "bar" | "plate" | "all"
lane_width = 133;
height = 118;              // top of the crossbar; camera plate adds ~12 mm
leg = 10; $fn = 32;

module leg() {
    difference() {
        union() {
            cube([leg, leg, height]);
            translate([-10, -10, 0]) cube([leg + 20, leg + 20, 3]);
        }
        translate([leg / 2, leg / 2, height - 10]) cylinder(d = 3.2, h = 11);   // bar screw
        for (x = [-5, leg + 5]) translate([x, leg / 2, -1]) cylinder(d = 3.2, h = 5);
    }
}

module bar() {
    span = lane_width + 2 * leg + 10;
    difference() {
        cube([span, leg, 6]);
        for (x = [leg / 2, span - leg / 2]) translate([x, leg / 2, -1]) cylinder(d = 3.4, h = 8);
        translate([span / 2, leg / 2, -1]) cylinder(d = 3.4, h = 8);          // hinge screw
    }
}

module plate() {
    difference() {
        union() {
            cube([50, 36, 3]);
            for (x = [17, 30]) translate([x, 0, 0]) cube([3, 6, 12]);           // hinge lugs
        }
        for (x = [17, 30]) translate([x - 1, 3, 8]) rotate([0, 90, 0]) cylinder(d = 3.4, h = 6);
        for (y = [12, 26]) translate([6, y, -1]) cube([38, 4, 5]);              // strap slots
        translate([25, 20, -1]) cylinder(d = 3.2, h = 5);
    }
}

if (part == "leg") leg();
else if (part == "bar") bar();
else if (part == "plate") plate();
else { leg(); translate([40, 0, 0]) leg(); translate([0, 40, 0]) bar(); translate([0, 60, 0]) plate(); }
