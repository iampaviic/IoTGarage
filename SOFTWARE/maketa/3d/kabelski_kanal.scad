// Cable channel with snap-on lid, glued under/along the base. Print several and chain them.
part = "all";   // "channel" | "lid" | "all"
length = 150; inner_w = 14; inner_h = 9; wall = 1.6;

module channel() {
    difference() {
        cube([length, inner_w + 2 * wall, inner_h + wall]);
        translate([-1, wall, wall]) cube([length + 2, inner_w, inner_h + 1]);
    }
    for (s = [0, 1]) translate([0, s * (inner_w + wall) + (s ? -0.6 : wall), inner_h + wall - 1.2])
        cube([length, 0.6, 1.2]);   // snap lips
}
module lid() {
    cube([length, inner_w + 2 * wall + 1.2, 1.2]);
    for (s = [0, 1]) translate([0, wall + 0.2 + s * (inner_w - 1.2), 1.2]) cube([length, 1.2, 2]);
}
if (part == "channel" || part == "all") channel();
if (part == "lid" || part == "all") translate([0, inner_w + 10, 0]) lid();
