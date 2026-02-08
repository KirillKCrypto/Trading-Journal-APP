from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from .. import db
from ..models import Task

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/tasks')
def task_list():
    active_tasks = Task.query.filter_by(completed=False).order_by(Task.id.desc()).all()
    return render_template('tasks/tasks_active.html', tasks=active_tasks)

@tasks_bp.route('/tasks/completed')
def completed_tasks():
    completed_tasks = Task.query.filter_by(completed=True).order_by(Task.id.desc()).all()
    return render_template('tasks/tasks_completed.html', tasks=completed_tasks)

@tasks_bp.route('/tasks/add', methods=['GET', 'POST'])
def add_task():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority')
        if title:
            task = Task(title=title, description=description, priority=priority)
            db.session.add(task)
            db.session.commit()
            return redirect(url_for('tasks.task_list'))
    return render_template('tasks/add.html')

@tasks_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.completed = not task.completed
    db.session.commit()
    return redirect(request.referrer or url_for('tasks.task_list'))

@tasks_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(request.referrer or url_for('tasks.task_list'))

@tasks_bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        task.priority = request.form.get('priority')
        db.session.commit()
        return redirect(url_for('tasks.task_list'))
    return render_template('tasks/edit.html', task=task)