/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class EisenhowerMatrixDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            moving: false,
            draggedActivityId: null,
            draggedFromQuadrant: null,
            dragOverQuadrant: null,
            cells: {
                do: {
                    key: "do",
                    title: _t("Do first"),
                    subtitle: _t("Urgent + Important"),
                    count: 0,
                    activities: [],
                },
                schedule: {
                    key: "schedule",
                    title: _t("Schedule"),
                    subtitle: _t("Important, not urgent"),
                    count: 0,
                    activities: [],
                },
                delegate: {
                    key: "delegate",
                    title: _t("Delegate"),
                    subtitle: _t("Urgent, not important"),
                    count: 0,
                    activities: [],
                },
                eliminate: {
                    key: "eliminate",
                    title: _t("Eliminate / Postpone"),
                    subtitle: _t("Not urgent, not important"),
                    count: 0,
                    activities: [],
                },
            },
        });

        this.limitPerQuadrant = 50;

        onWillStart(async () => {
            await this.loadData();
        });
    }

    get fieldsToRead() {
        return [
            "summary",
            "user_id",
            "date_deadline",
            "res_model",
            "res_id",
            "res_name_display",
            "activity_type_id",
            "eisenhower_quadrant",
            "priority_stars",
            "eisenhower_quadrant_sequence",
        ];
    }

    get quadrantKeys() {
        return Object.keys(this.state.cells);
    }

    async loadData() {
        this.state.loading = true;
        await Promise.all(this.quadrantKeys.map((key) => this.refreshQuadrant(key)));
        this.state.loading = false;
    }

    async refreshQuadrant(quadrantKey) {
        if (!this.state.cells[quadrantKey]) {
            return;
        }

        const domain = [["eisenhower_quadrant", "=", quadrantKey]];

        const [count, activities] = await Promise.all([
            this.orm.searchCount("mail.activity", domain),
            this.orm.searchRead("mail.activity", domain, this.fieldsToRead, {
                limit: this.limitPerQuadrant,
                order: "eisenhower_quadrant_sequence asc, priority_stars desc, date_deadline asc, id desc",
            }),
        ]);

        this.state.cells[quadrantKey].count = count;
        this.state.cells[quadrantKey].activities = activities;
    }

    openQuadrant(key) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.state.cells[key].title,
            res_model: "mail.activity",
            views: [
                [false, "tree"],
                [false, "form"],
                [false, "kanban"],
                [false, "pivot"],
                [false, "graph"],
            ],
            target: "current",
            domain: [["eisenhower_quadrant", "=", key]],
            context: { search_default_group_by_user: 1 },
        });
    }

    async openActivity(activityId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mail.activity",
            res_id: activityId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openRelatedRecord(activity) {
        if (!activity.res_model || !activity.res_id) {
            this.notification.add(_t("No related record available."), {
                type: "warning",
            });
            return;
        }

        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: activity.res_model,
            res_id: activity.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    isDragged(activityId) {
        return this.state.draggedActivityId === activityId;
    }

    isDropTarget(quadrantKey) {
        return this.state.dragOverQuadrant === quadrantKey;
    }

    getDeadlineBadgeClass(activity) {
        if (!activity.date_deadline) {
            return "text-bg-light border";
        }
        const today = new Date().toISOString().slice(0, 10);
        if (activity.date_deadline < today) {
            return "text-bg-danger";
        }
        if (activity.date_deadline === today) {
            return "text-bg-warning";
        }
        return "text-bg-light border";
    }

    getStarClass(activity, starNumber) {
        return activity.priority_stars >= starNumber
            ? "fa fa-star o_star_active"
            : "fa fa-star-o o_star_inactive";
    }

    async setPriority(activity, stars) {
        try {
            await this.orm.call("mail.activity", "action_set_priority_stars", [[activity.id], stars]);
            await this.refreshQuadrant(activity.eisenhower_quadrant);
            this.notification.add(_t("Priority updated."), { type: "success" });
        } catch (error) {
            this.notification.add(_t("Error while updating priority."), {
                type: "danger",
            });
            throw error;
        }
    }

    async moveUp(activity) {
        try {
            await this.orm.call("mail.activity", "action_move_up_in_quadrant", [[activity.id]]);
            await this.refreshQuadrant(activity.eisenhower_quadrant);
        } catch (error) {
            this.notification.add(_t("Unable to move the activity up."), {
                type: "danger",
            });
            throw error;
        }
    }

    async moveDown(activity) {
        try {
            await this.orm.call("mail.activity", "action_move_down_in_quadrant", [[activity.id]]);
            await this.refreshQuadrant(activity.eisenhower_quadrant);
        } catch (error) {
            this.notification.add(_t("Unable to move the activity down."), {
                type: "danger",
            });
            throw error;
        }
    }

    onDragStart(ev, activity, sourceQuadrant) {
        this.state.draggedActivityId = activity.id;
        this.state.draggedFromQuadrant = sourceQuadrant;
        this.state.dragOverQuadrant = null;

        if (ev.dataTransfer) {
            ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", String(activity.id));
        }
    }

    onDragEnd() {
        this.state.draggedActivityId = null;
        this.state.draggedFromQuadrant = null;
        this.state.dragOverQuadrant = null;
    }

    onDragOver(ev, targetQuadrant) {
        ev.preventDefault();
        this.state.dragOverQuadrant = targetQuadrant;
        if (ev.dataTransfer) {
            ev.dataTransfer.dropEffect = "move";
        }
    }

    onDragLeave(targetQuadrant) {
        if (this.state.dragOverQuadrant === targetQuadrant) {
            this.state.dragOverQuadrant = null;
        }
    }

    async onDrop(ev, targetQuadrant) {
        ev.preventDefault();

        const rawId =
            this.state.draggedActivityId ||
            (ev.dataTransfer ? parseInt(ev.dataTransfer.getData("text/plain"), 10) : null);

        const activityId = Number(rawId);
        const fromQuadrant = this.state.draggedFromQuadrant;

        this.state.dragOverQuadrant = null;

        if (!activityId || !targetQuadrant || !fromQuadrant) {
            this.onDragEnd();
            return;
        }

        if (fromQuadrant === targetQuadrant) {
            this.onDragEnd();
            return;
        }

        this.state.moving = true;
        try {
            await this.orm.write("mail.activity", [activityId], {
                eisenhower_quadrant: targetQuadrant,
            });
            await Promise.all([
                this.refreshQuadrant(fromQuadrant),
                this.refreshQuadrant(targetQuadrant),
            ]);
            this.notification.add(_t("Activity moved successfully."), {
                type: "success",
            });
        } catch (error) {
            this.notification.add(_t("Unable to move the activity."), {
                type: "danger",
            });
            throw error;
        } finally {
            this.state.moving = false;
            this.onDragEnd();
        }
    }
}

EisenhowerMatrixDashboard.template = "eisenhower_activity_matrix.Dashboard";

registry.category("actions").add("eisenhower_activity_matrix.dashboard", EisenhowerMatrixDashboard);
