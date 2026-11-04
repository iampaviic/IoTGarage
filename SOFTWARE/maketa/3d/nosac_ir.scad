// Holder for an FC-51 IR obstacle sensor at the barrier line (vehicle presence / safety).
// The sensor looks across the lane at bumper height; screw the base to the floor.
pcb_l = 31.5; pcb_w = 14.5; pcb_t = 1.8;
sensor_height = 18;   // centre of the IR LEDs above the floor (bumper height of 1:24 cars)
wall = 2; $fn = 32;

module nosac_ir() {
    difference() {
        union() {
            translate([-10, -12, 0]) cube([20, 24, 3]);                         // base
            translate([-wall - pcb_t / 2, -pcb_w / 2 - wall, 0])
                cube([pcb_t + 2 * wall, pcb_w + 2 * wall, sensor_height + pcb_l / 2]);
        }
        // vertical slot, LEDs at the top looking sideways
        translate([-pcb_t / 2, -pcb_w / 2, 3]) cube([pcb_t, pcb_w, 60]);
        for (y = [-7, 7]) translate([6, y, -1]) cylinder(d = 3.2, h = 5);
    }
}

nosac_ir();
