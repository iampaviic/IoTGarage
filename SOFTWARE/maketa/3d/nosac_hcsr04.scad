// HC-SR04 holder hanging under the ceiling bridge above a parking spot, sensor looking DOWN.
// The board (45 x 20 mm) slides in from the side; two screws fix the holder to the bridge.
// Print flat, no supports.
board_l = 45.5; board_w = 20.5; board_t = 1.8;
eye_d = 16.6; eye_pitch = 26;     // transducer diameter and centre distance
wall = 2; $fn = 64;

difference() {
    union() {
        translate([-board_l / 2 - wall, -board_w / 2 - wall, 0]) cube([board_l + 2 * wall, board_w + 2 * wall, 3 + board_t + 1.5]);
        // mounting ears
        for (s = [-1, 1]) translate([s * (board_l / 2 + wall + 5), 0, 0]) cylinder(d = 12, h = 3);
    }
    // transducers through the bottom
    for (s = [-1, 1]) translate([s * eye_pitch / 2, 0, -1]) cylinder(d = eye_d, h = 10);
    // board slot (open on one side so the pin header can stick out)
    translate([-board_l / 2, -board_w / 2, 3]) cube([board_l + wall + 1, board_w, board_t]);
    // space for components / crystal above the board
    translate([-board_l / 2 + 2, -board_w / 2 + 2, 3]) cube([board_l - 4, board_w - 4, 10]);
    for (s = [-1, 1]) translate([s * (board_l / 2 + wall + 5), 0, -1]) cylinder(d = 3.2, h = 5);
}
