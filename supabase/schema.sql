-- Create a table for User Profiles
create table public.profiles (
  id uuid references auth.users on delete cascade primary key,
  updated_at timestamp with time zone,
  full_name text,
  credits integer default 10 not null,
  subtitle_font_size integer default 24 not null,
  subtitle_font_color text default '#FFFFFF' not null,
  subtitle_font_style text default 'outline' not null
);

-- Enable Row Level Security for profiles
alter table public.profiles enable row level security;

create policy "Users can view their own profile." on public.profiles
  for select using (auth.uid() = id);

create policy "Users can update their own profile." on public.profiles
  for update using (auth.uid() = id);

-- Create a table for Uploaded Videos
create table public.videos (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users on delete cascade not null,
  name text not null,
  storage_path text not null,
  duration numeric default 0.0 not null,
  status text default 'pending' not null, -- 'pending', 'processing', 'completed', 'failed'
  error_message text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security for videos
alter table public.videos enable row level security;

create policy "Users can view their own videos." on public.videos
  for select using (auth.uid() = user_id);

create policy "Users can insert their own videos." on public.videos
  for insert with check (auth.uid() = user_id);

create policy "Users can update their own videos." on public.videos
  for update using (auth.uid() = user_id);

create policy "Users can delete their own videos." on public.videos
  for delete using (auth.uid() = user_id);

-- Create a table for Generated Viral Clips
create table public.clips (
  id uuid default gen_random_uuid() primary key,
  video_id uuid references public.videos on delete cascade not null,
  user_id uuid references auth.users on delete cascade not null,
  title text not null,
  hook text,
  reason text,
  content_type text,
  score integer default 0 not null,
  start_time numeric not null,
  end_time numeric not null,
  duration numeric not null,
  storage_path text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security for clips
alter table public.clips enable row level security;

create policy "Users can view their own clips." on public.clips
  for select using (auth.uid() = user_id);

create policy "Users can insert their own clips." on public.clips
  for insert with check (auth.uid() = user_id);

create policy "Users can update their own clips." on public.clips
  for update using (auth.uid() = user_id);

create policy "Users can delete their own clips." on public.clips
  for delete using (auth.uid() = user_id);

-- Trigger to automatically create a profile entry when a new user registers
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, full_name, credits)
  values (new.id, new.raw_user_meta_data->>'full_name', 10);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
