// Wheel stop: defines where the car stops in front of the barrier (repeatable camera view).
// Place it so the plate ends up on the stop line from nacrt/tlocrt.svg.
length = 110; $fn = 16;
module granicnik() {
    hull() {
        cube([length, 10, 1]);
        translate([0, 2.5, 0]) cube([length, 5, 7]);
    }
}

granicnik();
